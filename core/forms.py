from django import forms
from .models import FichaInscricao

class FichaInscricaoForm(forms.ModelForm):
    class Meta:
        model = FichaInscricao
        exclude = ['casal'] # Definido na view com base no usuário logado
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Adicionar classes do Bootstrap 5
        for field in self.fields.values():
            if type(field.widget) in (forms.CheckboxInput, forms.RadioSelect):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'
