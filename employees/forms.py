from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from .models import Employee, Department, LeaveRequest

STATUS_CHOICES = [
    ('ACTIVE', 'Active'),
    ('INACTIVE', 'Inactive'),
    ('ON_LEAVE', 'On Leave'),
]


class StyledAuthenticationForm(AuthenticationForm):
    """Login form with Bootstrap styling."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})


class NewUserForm(forms.ModelForm):
    """Form for creating a new Django User when HR adds an employee."""
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class EmployeeForm(forms.ModelForm):
    """ModelForm for creating / editing an Employee record."""

    # Override the ForeignKey field with a plain text input
    department = forms.CharField(max_length=100, required=False)

    class Meta:
        model = Employee
        fields = ['employee_id', 'job_role', 'shift', 'status', 'photo', 'phone', 'is_hr']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-populate the department text field when editing an existing employee
        if self.instance and self.instance.pk and self.instance.department:
            self.fields['department'].initial = self.instance.department.name
        for name, field in self.fields.items():
            if name == 'is_hr':
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        employee = super().save(commit=False)
        dept_name = self.cleaned_data.get('department', '').strip()
        if dept_name:
            dept, _ = Department.objects.get_or_create(
                name__iexact=dept_name,
                defaults={'name': dept_name},
            )
            employee.department = dept
        else:
            employee.department = None
        if commit:
            employee.save()
        return employee


class EmployeeSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    employee_id = forms.CharField(max_length=20)
    department = forms.CharField(max_length=100, required=False)
    job_role = forms.CharField(max_length=100)
    phone = forms.CharField(max_length=20, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def clean_employee_id(self):
        employee_id = self.cleaned_data['employee_id']
        if Employee.objects.filter(employee_id=employee_id).exists():
            raise forms.ValidationError("That Employee ID is already taken.")
        return employee_id

    def _resolve_department(self):
        """Look up or create a Department from the typed name."""
        name = self.cleaned_data.get('department', '').strip()
        if not name:
            return None
        dept, _ = Department.objects.get_or_create(
            name__iexact=name,
            defaults={'name': name},
        )
        return dept

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            Employee.objects.create(
                user=user,
                employee_id=self.cleaned_data['employee_id'],
                department=self._resolve_department(),
                job_role=self.cleaned_data['job_role'],
                phone=self.cleaned_data.get('phone', ''),
                is_hr=False,   # self-signup always creates a regular employee, never HR
            )
        return user


class MyProfileForm(forms.Form):
    """Form for employees to edit their own profile details."""
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20, required=False)
    department = forms.CharField(max_length=100, required=False)
    job_role = forms.CharField(max_length=100)
    photo = forms.ImageField(required=False)
    status = forms.ChoiceField(choices=STATUS_CHOICES)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.ClearableFileInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class LeaveRequestForm(forms.ModelForm):
    """Form for employees to apply for leave."""

    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Reason for leave…'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['leave_type'].widget.attrs.update({'class': 'form-select'})

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end = cleaned.get('end_date')
        if start and end and end < start:
            raise forms.ValidationError("End date cannot be before start date.")
        return cleaned