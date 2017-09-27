from django.conf.urls import url

from . import views

urlpatterns = [
    # general endpoints
    url(r'^$', views.index, name='index'),
    url(r'^users/$', views.users_view, name="users"),
    url(r'^users/(?P<userID>[0-9]+)/classes/$', views.all_user_classes, name="getall_user_classes"),
    url(r'^users/(?P<userID>[0-9]+)/classes/(?P<classID>[0-9]+)/exams/$', views.all_user_class_exams, name="getall_user_class_exams"),
    url(r'^users/(?P<userID>[0-9]+)/classes/(?P<classID>[0-9]+)/assignments/$', views.all_user_class_assignments, name="getall_user_class_assignments"),
    url(r'^users/(?P<userID>[0-9]+)/classes/(?P<classID>[0-9]+)/notes/$', views.all_user_class_notes, name="getall_user_class_notes"),
    # objectID specific endpoints
    url(r'^users/(?P<userID>[0-9]+)/classes/(?P<classID>[0-9]+)/$', views.user_class_material, name="get_user_class_material"),
    url(r'^users/(?P<userID>[0-9]+)/classes/(?P<classID>[0-9]+)/exams/(?P<examID>[0-9]+)/$', views.user_class_exam, name="get_user_class_exam"),
    url(r'^users/(?P<userID>[0-9]+)/classes/(?P<classID>[0-9]+)/assignments/(?P<assignmentID>[0-9]+)/$', views.user_class_assignment, name="get_user_class_assignment"),
    url(r'^users/(?P<userID>[0-9]+)/classes/(?P<classID>[0-9]+)/notes/(?P<noteID>[0-9]+)/$', views.user_class_note, name="get_user_class_note"),
    # upload endpoints
    url(r'^users/(?P<userID>[0-9]+)/classes/(?P<classID>[0-9]+)/assignments/(?P<courseMaterialID>[0-9]+)/upload/$', views.upload_course_material, name="upload_assignment"),
    url(r'^users/(?P<userID>[0-9]+)/classes/(?P<classID>[0-9]+)/notes/(?P<courseMaterialID>[0-9]+)/upload/$', views.upload_course_material, name="upload_note"),
    # user session endpoints
    url(r'^login/$', views.login_view, name="login"),
    url(r'^logout/', views.logout_view, name="logout"),
    ]
