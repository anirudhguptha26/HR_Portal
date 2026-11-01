from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    path('hr-dashboard/', views.hr_dashboard, name='hr_dashboard'),

    path('employees/', views.employee_list, name='employee_list'),
    path('employees/add/', views.employee_add, name='employee_add'),
    path('employees/<int:pk>/', views.employee_detail, name='employee_detail'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),

    path('my-profile/', views.my_profile, name='my_profile'),
    path('my-profile/edit/', views.my_profile_edit, name='my_profile_edit'),
    path('signup/', views.signup_view, name='signup'),

    # Leave requests
    path('leave/apply/', views.leave_request_create, name='leave_request_create'),
    path('leave/my-requests/', views.my_leave_requests, name='my_leave_requests'),
    path('leave/manage/', views.hr_leave_requests, name='hr_leave_requests'),
    path('leave/<int:pk>/action/', views.hr_leave_action, name='hr_leave_action'),
]
