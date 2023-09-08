from sqlalchemy import Column, Integer, String, ForeignKey
from database import Base

class Subject(Base):
    __tablename__ = 'subjects'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

class Class(Base):
    __tablename__ = 'classes'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    subject_id = Column(Integer, ForeignKey('subjects.id'))

class Student(Base):
    __tablename__ = 'students'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

class StudentClass(Base):
    __tablename__ = 'student_classes'

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    class_id = Column(Integer, ForeignKey('classes.id'))
    
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)