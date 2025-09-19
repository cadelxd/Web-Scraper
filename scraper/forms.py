from django import forms

class SearchForm(forms.Form):
    q = forms.CharField(
        label="Search topic",
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Enter a general topic and the app will fetch top web results, extract paragraphs, and show unique points.", "class": "form-control"})
    )
