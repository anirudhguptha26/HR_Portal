from django.db import models
from django.contrib.auth.models import User


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Employee(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        ON_LEAVE = "ON_LEAVE", "On Leave"

    class Shift(models.TextChoices):
        DAY = "DAY", "Day Shift"
        NIGHT = "NIGHT", "Night Shift"
        REGULAR = "REGULAR", "Regular Shift"

    # Link every employee record to a Django auth User so they can log in.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employee_profile")

    employee_id = models.CharField(max_length=20, unique=True)  # e.g. EMP001
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name="employees")
    job_role = models.CharField(max_length=100)  # e.g. "Software Engineer"
    shift = models.CharField(max_length=10, choices=Shift.choices, default=Shift.DAY)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    photo = models.ImageField(upload_to="employee_photos/", blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    date_joined = models.DateField(auto_now_add=True)

    # HR / super-admin flag. HR users can see and manage every employee.
    # Regular employees can only see their own record (enforced in views).
    is_hr = models.BooleanField(default=False)

    class Meta:
        ordering = ["employee_id"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.employee_id})"


class LeaveRequest(models.Model):
    class LeaveType(models.TextChoices):
        CASUAL = "CASUAL", "Casual Leave"
        SICK = "SICK", "Sick Leave"
        EARNED = "EARNED", "Earned Leave"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        DENIED = "DENIED", "Denied"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.CharField(max_length=10, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    hr_remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_leaves"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.employee} — {self.get_leave_type_display()} ({self.get_status_display()})"
