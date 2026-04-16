from django import forms
from .models import ApplicationTarget


class TargetAdminForm(forms.ModelForm):
    """Custom form for ApplicationTarget in admin"""
    
    class Meta:
        model = ApplicationTarget
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add time input widget for start and end time
        self.fields['work_start'].widget = forms.TimeInput(
            attrs={'type': 'time', 'class': 'vTimeField'},
            format='%H:%M'
        )
        self.fields['work_end'].widget = forms.TimeInput(
            attrs={'type': 'time', 'class': 'vTimeField'},
            format='%H:%M'
        )