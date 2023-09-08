from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import session
from models import *
from database import engine, SessionLocal, Base
from token_utils import *
from schemas import *
from auth_utils import *
from sqlalchemy.future import select
from config import *
import jwt
from redis import redis

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
app = FastAPI()

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    return username


@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    

@app.post("/token/", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.username == form_data.username))
        db_user = result.scalar_one_or_none()
        if not db_user or not verify_password(form_data.password, db_user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/subject/")
async def create_subject(subject: dict, current_user: str = Depends(get_current_user)):
    cached_subject = await redis.get(f"subject:{subject['name']}")
    if cached_subject:
        return cached_subject  

    async with SessionLocal() as session:
        async with session.begin():
            db_subject = Subject(name=subject["name"])
            session.add(db_subject)
        await session.commit()


        await redis.setex(f"subject:{subject['name']}", 10, db_subject.name)

        return db_subject
    
@app.get("/subject/{subject_id}")
async def read_subject(subject_id: int, current_user: str = Depends(get_current_user)):

    cached_subject = await redis.get(f"subject:{subject_id}")
    
    if cached_subject:
        return {"name": cached_subject.decode()}  

    async with SessionLocal() as session:
        db_subject = await session.get(Subject, subject_id)
        
        if not db_subject:
            raise HTTPException(status_code=404, detail="Subject not found")
        
        await redis.setex(f"subject:{subject_id}", 60, db_subject.name)
        
        return db_subject
    
@app.put("/subject/{subject_id}")
async def update_subject(subject_id: int, subject: dict, current_user: str = Depends(get_current_user)):
    async with SessionLocal() as session:
        db_subject = await session.get(Subject, subject_id)
        if not db_subject:
            raise HTTPException(status_code=404, detail="Subject not found")
        
        for key, value in subject.items():
            setattr(db_subject, key, value)
        
        await session.commit()
        
        await redis.setex(f"subject:{subject_id}", 60, db_subject.name)
        
        return db_subject

@app.delete("/subject/{subject_id}")
async def delete_subject(subject_id: int, current_user: str = Depends(get_current_user)):
    async with SessionLocal() as session:
        db_subject = await session.get(Subject, subject_id)
        if not db_subject:
            raise HTTPException(status_code=404, detail="Subject not found")
        
        session.delete(db_subject)
        await session.commit()
        
        await redis.delete(f"subject:{subject_id}")
        
        return {"detail": "Subject deleted successfully"}
    
    
@app.post("/student/")
async def create_student(student: dict, current_user: str = Depends(get_current_user)):
    async with SessionLocal() as session:
        db_student = Student(name=student["name"])
        session.add(db_student)
        await session.commit()
        await session.refresh(db_student)
        
        student_data = {"name": db_student.name}
        await redis.setex(f"student:{db_student.id}", 3600, json.dumps(student_data))
        
        return db_student
     
@app.get("/student/{student_id}")
async def read_student(student_id: int, current_user: str = Depends(get_current_user)):
    
    cached_student = await redis.get(f"student:{student_id}")
    
    if cached_student:
        return {"name": cached_student.decode("utf-8")}
    
    async with SessionLocal() as session:
        db_student = await session.get(Student, student_id)
        
        if not db_student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        await redis.setex(f"student:{student_id}", 3600, db_student.name)
    
    
@app.put("/student/{student_id}")
async def update_student(student_id: int, student: dict, current_user: str = Depends(get_current_user)):
    async with SessionLocal() as session:
        db_student = await session.get(Student, student_id)
        if not db_student:
            raise HTTPException(status_code=404, detail="Student not found")

        for key, value in student.items():
            setattr(db_student, key, value)

        await session.commit()

        await redis.setex(f"student:{student_id}", 3600, db_student.name)
        
        return {"name": db_student.name}
    
    
@app.delete("/student/{student_id}")
async def delete_student(student_id: int, current_user: str = Depends(get_current_user)):
    async with SessionLocal() as session:
        db_student = await session.get(Student, student_id)
        if not db_student:
            raise HTTPException(status_code=404, detail="Student not found")
        session.delete(db_student)
        await session.commit()

        await redis.delete(f"student:{student_id}")
        
        return {"detail": "Student deleted successfully"}
    
    
    
@app.post("/class/")
async def create_class(class_data: dict, current_user: str = Depends(get_current_user)):
    async with SessionLocal() as session:
        db_class = Class(name=class_data["name"], subject_id=class_data["subject_id"])
        session.add(db_class)
        await session.commit()
        await session.refresh(db_class)
        await redis.setex(f"class:{db_class.id}", 3600, db_class.name)

        return {"name": db_class.name, "subject_id": db_class.subject_id}
    

@app.get("/class/{class_id}")
async def read_class(class_id: int, current_user: str = Depends(get_current_user)):
    class_name = await redis.get(f"class:{class_id}")

    if class_name:
        return {"id": class_id, "name": class_name.decode("utf-8")}

    async with SessionLocal() as session:
        db_class = await session.get(Class, class_id)
        if not db_class:
            raise HTTPException(status_code=404, detail="Class not found")

        await redis.setex(f"class:{class_id}", 3600, db_class.name)
        
        return {"id": db_class.id, "name": db_class.name, "subject_id": db_class.subject_id}
    
    
@app.put("/class/{class_id}")
async def update_class(class_id: int, class_data: dict, current_user: str = Depends(get_current_user)):
    async with SessionLocal() as session:
        db_class = await session.get(Class, class_id)
        if not db_class:
            raise HTTPException(status_code=404, detail="Class not found")

        for key, value in class_data.items():
            setattr(db_class, key, value)

        await session.commit()

        await redis.setex(f"class:{class_id}", 3600, db_class.name)

        return {"id": db_class.id, "name": db_class.name, "subject_id": db_class.subject_id}
    
    

@app.delete("/class/{class_id}")
async def delete_class(class_id: int, current_user: str = Depends(get_current_user)):
    async with SessionLocal() as session:
        db_class = await session.get(Class, class_id)
        if not db_class:
            raise HTTPException(status_code=404, detail="Class not found")
        
        session.delete(db_class)
        await session.commit()
        await redis.delete(f"class:{class_id}")

        return {"detail": "Class deleted successfully"}
    
    
@app.post("/studentclass/")
async def create_studentclass(studentclass_data: dict, current_user: str = Depends(get_current_user)):
    async with SessionLocal() as session:
        db_studentclass = StudentClass(student_id=studentclass_data["student_id"], class_id=studentclass_data["class_id"])
        session.add(db_studentclass)
        await session.commit()
        await session.refresh(db_studentclass)
        
        student_id = studentclass_data["student_id"]
        class_id = studentclass_data["class_id"]
        await redis.setex(f"studentclass:{student_id}:{class_id}", 3600, "true")

        return {"student_id": db_studentclass.student_id, "class_id": db_studentclass.class_id}
        
@app.get("/studentclass/{studentclass_id}")
async def read_studentclass(studentclass_id: int, current_user: str = Depends(get_current_user)):
    studentclass_data = await redis.get(f"studentclass:{studentclass_id}")
    
    if studentclass_data:
        return studentclass_data 

    async with SessionLocal() as session:
        db_studentclass = await session.get(StudentClass, studentclass_id)
        if not db_studentclass:
            raise HTTPException(status_code=404, detail="StudentClass not found")
        
        await redis.setex(f"studentclass:{studentclass_id}", 3600, {"student_id": db_studentclass.student_id, "class_id": db_studentclass.class_id})

        return {"student_id": db_studentclass.student_id, "class_id": db_studentclass.class_id}
    


@app.put("/studentclass/{studentclass_id}")
async def update_studentclass(studentclass_id: int, studentclass_data: dict, current_user: str = Depends(get_current_user)):
    async with SessionLocal() as session:
        db_studentclass = await session.get(StudentClass, studentclass_id)
        if not db_studentclass:
            raise HTTPException(status_code=404, detail="StudentClass not found")

        for key, value in studentclass_data.items():
            setattr(db_studentclass, key, value)

        await session.commit()
        
        await redis.setex(f"studentclass:{studentclass_id}", 3600, {"student_id": db_studentclass.student_id, "class_id": db_studentclass.class_id})
        
        return {"student_id": db_studentclass.student_id, "class_id": db_studentclass.class_id}
    
    
@app.delete("/studentclass/{studentclass_id}")
async def delete_studentclass(studentclass_id: int, current_user: str = Depends(get_current_user)):
    async with SessionLocal() as session:
        db_studentclass = await session.get(StudentClass, studentclass_id)
        if not db_studentclass:
            raise HTTPException(status_code=404, detail="StudentClass not found")
        
        await redis.delete(f"studentclass:{studentclass_id}")
        
        session.delete(db_studentclass)
        await session.commit()
        return {"detail": "StudentClass deleted successfully"}