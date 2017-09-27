from django.db import models
from django.contrib.auth.models import User
from django.forms.models import model_to_dict



class Course(models.Model):
    # TODO: Integrate Django Users with our stuff
    courseID = models.AutoField(primary_key=True)
    userID = models.ForeignKey(User, on_delete=models.DO_NOTHING, db_column="userID")
    courseNumber = models.CharField(max_length=50)
    courseName = models.CharField(max_length=50)
    instructor = models.CharField(max_length=50)
    color = models.CharField(max_length=6)


class Exam(models.Model):
    examID = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    date = models.DateField()
    courseID = models.ForeignKey(Course, on_delete=models.DO_NOTHING, db_column="courseID")


class CourseMaterial(models.Model):
    courseMaterialID = models.AutoField(primary_key=True)
    type = models.CharField(max_length=50, default="assignment")
    name = models.CharField(max_length=50)
    date = models.DateField()
    assocExamID = models.ForeignKey(Exam, null=True, db_column="assocExamID")
    courseID = models.ForeignKey(Course, on_delete=models.DO_NOTHING, db_column="courseID")


class UserFiles(models.Model):
    fileID = models.AutoField(primary_key=True)
    assocCourseMaterialID = models.ForeignKey(CourseMaterial, null=True, db_column="assocCourseMaterialID")
    url = models.CharField(max_length=2000)
    label = models.CharField(max_length=50)
