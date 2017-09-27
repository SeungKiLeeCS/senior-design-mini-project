from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest, HttpResponse
from django.conf import settings
from django.forms.models import model_to_dict
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from functools import wraps
import boto3
import datetime
import json

from API.models import *


########## HELPER FUNCTIONS ##########

def login_required_no_redirect(func):
    """Returns a 401 if the user is not authenticated, otherwise allows the view to execute. Used as a decorator"""
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated():
            return func(request, *args, **kwargs)
        else:
            return HttpResponse("Login required to access this resource", status=401)
    return wrapper


def require_post_params(required_post_param_list):
    """Given a list of parameters, decorate a function to require a list of parameters be sent in the POST body"""
    def decorator(func):
        @wraps(func)
        def inner(request, *args, **kwargs):
            if request.method == "POST":
                body = json.loads(request.body.decode("utf-8"))
                for param in required_post_param_list:
                    if body.get(param, None) is None:  # if a element in the required parameters is not in POST body
                        return HttpResponseBadRequest("Missing parameters - required parameters are {}"
                                                      .format(required_post_param_list), status=400)
            # if execution makes it here, all required params are present, allow view to execute as normal
            return func(request, *args, **kwargs)
        return inner
    return decorator


"""Currently populated with dummy endpoints"""
_dummy_data = settings.DUMMY_DATA

# datetime utility function
def datetime_handler(x):
    if hasattr(x, 'isoformat'):
        return x.isoformat()
    else:
        raise TypeError


def check_params(func):
    """Add this decorator to the beginning of a view to get the kwargs (from URL parameters)
    that will be passed to the view"""
    def wrapper(request, *args, **kwargs):
        return HttpResponse(str(list(**kwargs)))
    return wrapper


def restrict_endpoint_resources_to_owner(func):
    """If userID is an argument in the view, check that against the currently logged in user's id.
    If they match, accept the request, if not return 403 Unauthorized

    Use AFTER require login decorator"""
    def wrapper(request, *args, **kwargs):
        if str(request.user.id) == kwargs["userID"]:
            return func(request, *args, **kwargs)
        else:
            return HttpResponse("You are not authorized to access that resource", status=403)

    return wrapper


######### VIEWS ##########


def index(request):
    # return HttpResponse(str(settings.DUMMY_DATA))
    return HttpResponse("Hello, world. You're at the API index.")

@login_required_no_redirect
def upload_course_material(request, userID, classID, courseMaterialID):
    if request.method == "POST":
        s3 = boto3.client('s3')
        for key in request.FILES:
            filedata = request.FILES[key]
            filename = "{0}/{1}/{2}/{3}".format(userID,classID,courseMaterialID,key)
            s3.upload_fileobj(filedata, 'swimmingfish', filename)
            # store link in DB
            assocCourseMaterial = CourseMaterial.objects.get(courseMaterialID=courseMaterialID)
            object_url = "https://s3.amazonaws.com/swimmingfish/{}".format(filename)
            f = UserFiles(
                assocCourseMaterialID=assocCourseMaterial,
                url=object_url,
                label=filename
            )
            f.save()
            return HttpResponse(json.dumps({"link":object_url}), status=201)
        return HttpResponse("Upload failed - improper POST format", status=401)
    else:
        return HttpResponse("Upload a file here", status=404)


# List all users (no regular user would have access to this) or create a user
# POST /users
@require_post_params(["username", "password"])
def users_view(request):
    if request.method == "GET":
        return HttpResponse("Not yet implemented", status=501)
    else:
        # create a user
        body = json.loads(request.body.decode("utf-8"))
        if not User.objects.filter(username=body["username"]).exists():
            user = User.objects.create_user(username=body["username"],
                                            password=body["password"],
                                            email=body.get("email", None),
                                            first_name=body.get("firstName", None),  # not required
                                            last_name=body.get("lastName", None)  # not required
                                            )
            user.save()
            return HttpResponse(json.dumps({"userID": user.id}), status=201)
        else:
            return HttpResponse("That username already exists", status=409)



### Login ###
# POST /login
@require_post_params(["username", "password"])
def login_view(request):
    if request.method == "GET":
        return HttpResponse(status=404)
    else:
        body = json.loads(request.body.decode("utf-8"))
        user = authenticate(username=body["username"], password=body["password"])

        if user is not None:
            login(request, user)
            return HttpResponse(json.dumps({"userID": user.id}), status=201)
        else:
            return HttpResponse("Invalid username/password combination", status=401)


### Logout ###
# POST /logout
def logout_view(request):
    if request.method == "GET":
        return HttpResponse(status=404)
    else:
        logout(request)
        return HttpResponse("You're logged out", status=201)


##### GET OR POST A CLASS #####
# GET /users/{userID}/classes
@login_required_no_redirect
@restrict_endpoint_resources_to_owner
@require_post_params(["courseName"])
def all_user_classes(request, userID):
    if request.method == "GET":
        response = []
        classes = Course.objects.all().filter(userID=userID)

        # create class level of object
        for c in classes:
            response_dict = model_to_dict(c)
            # response_dict = {key: c_dict[key] for key in c_dict}
            response_dict["exams"] = []
            exams = c.exam_set.all()

            # create exam level of class
            for e in exams:
                e_dict = model_to_dict(e)
                e_dict["assignments"] = []
                e_dict["notes"] = []

                # populate lists in each exam object
                materials = e.coursematerial_set.all()
                for m in materials:
                    material_dict = model_to_dict(m)
                    if material_dict["type"] == "note":
                        e_dict["notes"].append(material_dict)
                    else:  # material_dict["type"] == "assignment
                        e_dict["assignments"].append(material_dict)
                response_dict["exams"].append(e_dict)

            response_dict["materialWithoutExam"] = []
            materials = c.coursematerial_set.filter(assocExamID=None)
            for m in materials:
                response_dict["materialWithoutExam"].append(model_to_dict(m))

            response.append(response_dict)

        return HttpResponse(json.dumps(response, default=datetime_handler), content_type="application/json", status=200)
    else:  # request.method == "POST"
        # create a dict from the request body (expecting json)
        body = json.loads(request.body.decode("utf-8"))

        # todo: better parameter validation/error handling
        assoc_user = User.objects.get(id=userID)
        # this statement is akin to running INSERT INTO Course VALUES (etc)
        # It is executed within a transaction, and changes/additions which are made will not be reflected until the commit
        # which is executed by executing c.save(). This is the same for one object as it is for many, for both inserts and updates
        c = Course(courseName=body["courseName"],
                   instructor=body.get("instructor", None),
                   userID=assoc_user,
                   color="039BE5", # todo figure out best way to assign color
                   courseNumber=body.get("courseNumber", None)
                   )

        # before calling c.save(), it does not have a courseID assigned, but after the insert, it does.
        # We can use c as the object to get the return data for.
        c.save()

        # this syntax is assuming that the DB fields are named exactly as they are in the response
        # this will not always be the case, so watch out for that
        response = model_to_dict(c)
        return HttpResponse(json.dumps(response), content_type="application/json", status=201)

##### GET OR POST AN EXAM FOR A CLASS #####
# GET /users/{userID}/classes/{classID}/exams/
@login_required_no_redirect
@restrict_endpoint_resources_to_owner
@require_post_params(["name"])
def all_user_class_exams(request, userID, classID):
    if request.method == "GET":
        response = []
        exams = Exam.objects.filter(courseID=classID, courseID__userID=userID)  # reverse foreign key lookup
        for e in exams:
            e_dict = model_to_dict(e)
            e_dict["assignments"] = []
            e_dict["notes"] = []

            materials = e.coursematerial_set.all()
            for m in materials:
                material_dict = model_to_dict(m)
                if material_dict["type"] == "note":
                    e_dict["notes"].append(material_dict)
                else:  # material_dict["type"] == "assignment
                    e_dict["assignments"].append(material_dict)
            response.append(e_dict)

        return HttpResponse(json.dumps(response, default=datetime_handler), content_type="application/json", status=200)
    else:
        body = json.loads(request.body.decode("utf-8"))
        assocCourse = Course.objects.get(courseID=classID)
        e = Exam(name=body["name"], date=body.get("date", None), courseID=assocCourse)
        e.save()

        response = model_to_dict(e)

        return HttpResponse(json.dumps(response), content_type="application/json", status=201)

##### GET OR POST AN ASSIGNMENT FOR A CLASS #####
# GET /users/{userID}/classes/{classID}/assignments/
@login_required_no_redirect
@restrict_endpoint_resources_to_owner
@require_post_params(["name"])
def all_user_class_assignments(request, userID, classID):
    if request.method == "GET":
        response = []
        assignments = CourseMaterial.objects.filter(courseID=classID, type="assignment", courseID__userID=userID)
        for a in assignments:
            response.append(model_to_dict(a))

        return HttpResponse(json.dumps(response, default=datetime_handler), content_type="application/json", status=200)
    else:
        body = json.loads(request.body.decode("utf-8"))
        assocExam = None
        if "assocExamID" in body:
            assocExam = Exam.objects.get(examID=body["assocExamID"])
        assocCourse = Course.objects.get(courseID=classID)
        a = CourseMaterial(name=body["name"], date=body.get("date", None), type="assignment", courseID=assocCourse,
                           assocExamID=assocExam)
        a.save()

        response = model_to_dict(a)
        return HttpResponse(json.dumps(response), content_type="application/json", status=201)


##### GET OR POST A NOTE FOR A CLASS #####
# GET /users/{userID}/classes/{classID}/notes/
@login_required_no_redirect
@restrict_endpoint_resources_to_owner
@require_post_params(["name"])
def all_user_class_notes(request, userID, classID):
    if request.method == "GET":
        response = []
        notes = CourseMaterial.objects.filter(courseID=classID, type="note", courseID__userID=userID)
        for n in notes:
            response.append(model_to_dict(n))

        return HttpResponse(json.dumps(response, default=datetime_handler), content_type="application/json", status=200)
    else:
        body = json.loads(request.body.decode("utf-8"))
        assocExam = None
        if "assocExamID" in body:
            assocExam = Exam.objects.get(examID=body["assocExamID"])
        assocCourse = Course.objects.get(courseID=classID)
        n = CourseMaterial(name=body["name"], date=body.get("date", None), type="note", courseID=assocCourse,
                           assocExamID=assocExam)
        n.save()

        response = model_to_dict(n)
        return HttpResponse(json.dumps(response), content_type="application/json", status=201)


##### GET ALL MATERIALS FOR SINGLE CLASS #####
# GET /users/{userID}/classes/{classID}
@login_required_no_redirect
@restrict_endpoint_resources_to_owner
def user_class_material(request, userID, classID):
    if request.method == "GET": # endpoint only accepts a GET request
        response = {"exams": []}

        course = Course.objects.get(courseID=classID, userID=userID)

        course_dict = model_to_dict(course)
        for key in course_dict:
            response[key] = course_dict[key]

        exams = course.exam_set.all()
        for e in exams:
            exam_dict = model_to_dict(e)
            exam_dict["assignments"] = []
            assignments = e.coursematerial_set.filter(type="assignment")
            for a in assignments:
                exam_dict["assignments"].append(model_to_dict(a))

            exam_dict["notes"] = []
            notes = e.coursematerial_set.filter(type="note")

            for n in notes:
                exam_dict["notes"].append(model_to_dict(n))

            response["exams"].append(exam_dict)

        response["materialWithoutExam"] = []
        materials = course.coursematerial_set.filter(assocExamID=None)
        for m in materials:
            response["materialWithoutExam"].append(model_to_dict(m))

        return HttpResponse(json.dumps(response, default=datetime_handler), content_type="application/json", status=200)
    else:
        return HttpResponse("Not yet implemented", status=501)


##### GET SINGLE EXAM #####
# GET /users/{userID}/classes/{classID}/exams/{examID}
@login_required_no_redirect
@restrict_endpoint_resources_to_owner
def user_class_exam(request, userID, classID, examID):
    if request.method == "GET":
        exam = Exam.objects.get(examID=examID, courseID__userID=userID)
        response = model_to_dict(exam)

        response["assignments"] = []
        assignments = exam.coursematerial_set.filter(type="assignment")
        for a in assignments:
            response["assignments"].append(model_to_dict(a))

        response["notes"] = []
        notes = exam.coursematerial_set.filter(type="note")
        for n in notes:
            response["notes"].append(model_to_dict(n))

        return HttpResponse(json.dumps(response, default=datetime_handler), content_type="application/json", status=200)
    else:
        return HttpResponse("Not yet implemented", status=501)


##### GET SINGLE ASSIGNMENT ENDPOINT #####
# GET /users/{userID}/classes/{classID}/assignments/{courseMaterialID}
@login_required_no_redirect
@restrict_endpoint_resources_to_owner
def user_class_assignment(request, userID, classID, assignmentID):
    if request.method == "GET":
        assignment = CourseMaterial.objects.get(courseMaterialID=assignmentID, courseID__userID=userID, courseID=classID)

        response = model_to_dict(assignment)
        return HttpResponse(json.dumps(response, default=datetime_handler), content_type="application/json", status=200)
    else:
        return HttpResponse("Not yet implemented", status=501)


##### GET SINGLE NOTE ENDPOINT #####
# GET /users/{userID}/classes/{classID}/notes/{noteID}
@login_required_no_redirect
@restrict_endpoint_resources_to_owner
def user_class_note(request, userID, classID, noteID):
    if request.method == "GET":
        note = CourseMaterial.objects.get(courseMaterialID=noteID, courseID__userID=userID, courseID=classID)

        response = model_to_dict(note)
        return HttpResponse(json.dumps(response, default=datetime_handler), content_type="application/json", status=200)
    else:
        return HttpResponse("Not yet implemented", status=501)
