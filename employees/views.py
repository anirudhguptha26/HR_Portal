from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from .models import Employee, Department, LeaveRequest
from .forms import EmployeeForm, NewUserForm, StyledAuthenticationForm, EmployeeSignUpForm, MyProfileForm, LeaveRequestForm


def is_hr_user(user):
    return hasattr(user, 'employee_profile') and user.employee_profile.is_hr


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = StyledAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect('dashboard')
        messages.error(request, "Invalid username or password.")
    else:
        form = StyledAuthenticationForm()
    return render(request, 'employees/login.html', {'form': form})


def logout_view(request):
    auth_logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    # HR goes to the dashboard overview; regular employees go to their own profile
    if is_hr_user(request.user):
        return redirect('hr_dashboard')
    return redirect('my_profile')


@login_required
@user_passes_test(is_hr_user, login_url='dashboard')
def hr_dashboard(request):
    """Summary dashboard for HR with status-based employee counts."""
    total = Employee.objects.count()
    active = Employee.objects.filter(status='ACTIVE').count()
    inactive = Employee.objects.filter(status='INACTIVE').count()
    on_leave = Employee.objects.filter(status='ON_LEAVE').count()
    pending_leaves = LeaveRequest.objects.filter(status='PENDING').count()

    context = {
        'total_count': total,
        'active_count': active,
        'inactive_count': inactive,
        'on_leave_count': on_leave,
        'pending_leave_count': pending_leaves,
    }
    return render(request, 'employees/hr_dashboard.html', context)


@login_required
@user_passes_test(is_hr_user, login_url='dashboard')
def employee_list(request):
    employees = Employee.objects.select_related('user', 'department')

    query = request.GET.get('q', '')
    department_id = request.GET.get('department', '')
    status = request.GET.get('status', '')

    if query:
        employees = employees.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(employee_id__icontains=query)
        )
    if department_id:
        employees = employees.filter(department_id=department_id)
    if status:
        employees = employees.filter(status=status)

    context = {
        'employees': employees,
        'departments': Department.objects.all(),
        'status_choices': Employee.Status.choices,
        'total_count': Employee.objects.count(),
        'query': query,
        'selected_department': department_id,
        'selected_status': status,
    }
    return render(request, 'employees/employee_list.html', context)


@login_required
@user_passes_test(is_hr_user, login_url='dashboard')
def employee_detail(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    return render(request, 'employees/employee_detail.html', {'employee': employee})


@login_required
@user_passes_test(is_hr_user, login_url='dashboard')
def employee_add(request):
    if request.method == 'POST':
        user_form = NewUserForm(request.POST)
        emp_form = EmployeeForm(request.POST, request.FILES)
        if user_form.is_valid() and emp_form.is_valid():
            user = user_form.save()
            employee = emp_form.save(commit=False)
            employee.user = user
            employee.save()
            messages.success(request, f"Employee {employee.employee_id} added.")
            return redirect('employee_list')
    else:
        user_form = NewUserForm()
        emp_form = EmployeeForm()
    return render(request, 'employees/employee_form.html',
                  {'user_form': user_form, 'emp_form': emp_form, 'is_new': True})


@login_required
@user_passes_test(is_hr_user, login_url='dashboard')
def employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        emp_form = EmployeeForm(request.POST, request.FILES, instance=employee)
        if emp_form.is_valid():
            emp_form.save()
            messages.success(request, "Employee updated.")
            return redirect('employee_detail', pk=employee.pk)
    else:
        emp_form = EmployeeForm(instance=employee)
    return render(request, 'employees/employee_form.html',
                  {'emp_form': emp_form, 'is_new': False, 'employee': employee})


@login_required
@user_passes_test(is_hr_user, login_url='dashboard')
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        employee.user.delete()  # cascades to Employee
        messages.success(request, "Employee removed.")
        return redirect('employee_list')
    return render(request, 'employees/employee_confirm_delete.html', {'employee': employee})


@login_required
def my_profile(request):
    # Every employee (HR or not) can view their own record here
    employee = get_object_or_404(Employee, user=request.user)
    return render(request, 'employees/my_profile.html', {'employee': employee})


@login_required
def my_profile_edit(request):
    employee = get_object_or_404(Employee, user=request.user)
    if request.method == 'POST':
        form = MyProfileForm(request.POST, request.FILES)
        if form.is_valid():
            # Update User fields
            user = request.user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()

            # Update Employee fields
            employee.phone = form.cleaned_data.get('phone', '')
            employee.job_role = form.cleaned_data['job_role']
            employee.status = form.cleaned_data['status']

            # Resolve department
            dept_name = form.cleaned_data.get('department', '').strip()
            if dept_name:
                dept, _ = Department.objects.get_or_create(
                    name__iexact=dept_name,
                    defaults={'name': dept_name},
                )
                employee.department = dept
            else:
                employee.department = None

            # Photo
            if form.cleaned_data.get('photo'):
                employee.photo = form.cleaned_data['photo']

            employee.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('my_profile')
    else:
        form = MyProfileForm(initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'phone': employee.phone,
            'department': employee.department.name if employee.department else '',
            'job_role': employee.job_role,
            'status': employee.status,
        })
    return render(request, 'employees/my_profile_edit.html', {'form': form, 'employee': employee})

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = EmployeeSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, "Account created successfully.")
            return redirect('dashboard')
    else:
        form = EmployeeSignUpForm()
    return render(request, 'employees/signup.html', {'form': form})


# ────────────────────── Leave Request Views ──────────────────────

@login_required
def leave_request_create(request):
    """Employee submits a new leave request."""
    employee = get_object_or_404(Employee, user=request.user)
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = employee
            leave.save()
            messages.success(request, "Leave request submitted successfully.")
            return redirect('my_leave_requests')
    else:
        form = LeaveRequestForm()
    return render(request, 'employees/leave_request_form.html', {'form': form})


@login_required
def my_leave_requests(request):
    """Employee views their own leave requests."""
    employee = get_object_or_404(Employee, user=request.user)
    leaves = employee.leave_requests.all()
    return render(request, 'employees/my_leave_requests.html', {'leaves': leaves})


@login_required
@user_passes_test(is_hr_user, login_url='dashboard')
def hr_leave_requests(request):
    """HR views all leave requests."""
    status_filter = request.GET.get('status', '')
    leaves = LeaveRequest.objects.select_related('employee__user', 'reviewed_by__user')
    if status_filter:
        leaves = leaves.filter(status=status_filter)
    pending_count = LeaveRequest.objects.filter(status='PENDING').count()
    context = {
        'leaves': leaves,
        'pending_count': pending_count,
        'selected_status': status_filter,
        'status_choices': LeaveRequest.Status.choices,
    }
    return render(request, 'employees/hr_leave_requests.html', context)


@login_required
@user_passes_test(is_hr_user, login_url='dashboard')
def hr_leave_action(request, pk):
    """HR approves or denies a leave request."""
    leave = get_object_or_404(LeaveRequest, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action in ('APPROVED', 'DENIED'):
            leave.status = action
            leave.hr_remarks = request.POST.get('hr_remarks', '')
            leave.reviewed_by = request.user.employee_profile
            leave.reviewed_at = timezone.now()
            leave.save()

            # Update employee status accordingly
            employee = leave.employee
            if action == 'APPROVED':
                employee.status = 'ON_LEAVE'
                employee.save()
            elif action == 'DENIED' and employee.status == 'ON_LEAVE':
                employee.status = 'ACTIVE'
                employee.save()

            label = 'approved' if action == 'APPROVED' else 'denied'
            messages.success(request, f"Leave request {label}.")
    return redirect('hr_leave_requests')
