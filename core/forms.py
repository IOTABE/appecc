from django import forms
from .models import FichaInscricao, Casal, Encontro, MovimentacaoFinanceira, ContaContabil, LancamentoContabil


class FichaInscricaoForm(forms.ModelForm):
    nome_marido = forms.CharField(max_length=80, label="Nome Completo do Marido")
    nome_esposa = forms.CharField(max_length=80, label="Nome Completo da Esposa")
    celular_marido = forms.CharField(max_length=20, required=False, label="Celular do Marido")
    celular_esposa = forms.CharField(max_length=20, required=False, label="Celular da Esposa")

    class Meta:
        model = FichaInscricao
        exclude = ['casal', 'encontro', 'numero_ficha']
        widgets = {
            'data_nascimento_marido': forms.DateInput(attrs={'type': 'date'}),
            'data_nascimento_esposa': forms.DateInput(attrs={'type': 'date'}),
            'data_casamento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.casal = kwargs.pop('casal', None)
        super().__init__(*args, **kwargs)

        if self.casal:
            self.fields['nome_marido'].initial = self.casal.nome_marido
            self.fields['nome_esposa'].initial = self.casal.nome_esposa
            self.fields['celular_marido'].initial = self.casal.celular_marido
            self.fields['celular_esposa'].initial = self.casal.celular_esposa
            self.fields['casal_convidou'].queryset = Casal.objects.filter(associado=True)

        if 'casal_convidou' in self.fields:
            self.fields['casal_convidou'].queryset = Casal.objects.filter(associado=True)

        for field in self.fields.values():
            if type(field.widget) in (forms.CheckboxInput, forms.RadioSelect):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'

    def save_casal_fields(self):
        if self.casal:
            self.casal.nome_marido = self.cleaned_data.get('nome_marido', '')
            self.casal.nome_esposa = self.cleaned_data.get('nome_esposa', '')
            self.casal.celular_marido = self.cleaned_data.get('celular_marido', '')
            self.casal.celular_esposa = self.cleaned_data.get('celular_esposa', '')
            self.casal.save(update_fields=[
                'nome_marido', 'nome_esposa',
                'celular_marido', 'celular_esposa',
            ])


class EncontroForm(forms.ModelForm):
    class Meta:
        model = Encontro
        fields = ['numero', 'data_inicio', 'data_fim', 'status']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'}),
            'data_fim': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if type(field.widget) in (forms.CheckboxInput, forms.RadioSelect):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'


class MovimentacaoForm(forms.ModelForm):
    class Meta:
        model = MovimentacaoFinanceira
        fields = ['encontro', 'descricao', 'valor_total']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['encontro'].queryset = Encontro.objects.order_by('-numero')
        for field in self.fields.values():
            if type(field.widget) in (forms.CheckboxInput, forms.RadioSelect):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'


class ContaContabilForm(forms.ModelForm):
    class Meta:
        model = ContaContabil
        fields = ['codigo', 'nome', 'tipo', 'nivel', 'conta_pai']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'nivel' in self.data and self.data['nivel']:
            nivel = int(self.data['nivel'])
            if nivel == 1:
                self.fields['conta_pai'].queryset = ContaContabil.objects.none()
            elif nivel == 2:
                self.fields['conta_pai'].queryset = ContaContabil.objects.filter(nivel=1)
            elif nivel == 3:
                self.fields['conta_pai'].queryset = ContaContabil.objects.filter(nivel=2)
        elif self.instance.pk:
            if self.instance.nivel == 1:
                self.fields['conta_pai'].queryset = ContaContabil.objects.none()
            elif self.instance.nivel == 2:
                self.fields['conta_pai'].queryset = ContaContabil.objects.filter(nivel=1)
            elif self.instance.nivel == 3:
                self.fields['conta_pai'].queryset = ContaContabil.objects.filter(nivel=2)
        else:
            self.fields['conta_pai'].queryset = ContaContabil.objects.none()

        for field in self.fields.values():
            if type(field.widget) in (forms.CheckboxInput, forms.RadioSelect):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        nivel = cleaned_data.get('nivel')
        conta_pai = cleaned_data.get('conta_pai')

        if nivel == 1 and conta_pai:
            raise forms.ValidationError("Conta de nível 1 não pode ter conta pai.")
        if nivel == 2 and not conta_pai:
            raise forms.ValidationError("Conta de nível 2 deve ter uma conta pai (nível 1).")
        if nivel == 3:
            if not conta_pai:
                raise forms.ValidationError("Conta de nível 3 deve ter conta pai (nível 2).")
            if not conta_pai.conta_pai:
                raise forms.ValidationError("A conta pai (nível 2) deve pertencer a uma conta nível 1.")
        return cleaned_data


class LancamentoContabilForm(forms.ModelForm):
    class Meta:
        model = LancamentoContabil
        fields = ('conta', 'tipo', 'valor')
        widgets = {
            'conta': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['conta'].queryset = ContaContabil.objects.filter(nivel=3)


LancamentoContabilFormSet = forms.inlineformset_factory(
    MovimentacaoFinanceira,
    LancamentoContabil,
    form=LancamentoContabilForm,
    fields=('conta', 'tipo', 'valor'),
    extra=2,
    can_delete=True,
    widgets={
        'conta': forms.Select(attrs={'class': 'form-select'}),
        'tipo': forms.Select(attrs={'class': 'form-select'}),
        'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    }
)


class ConviteRegistroForm(forms.ModelForm):
    nome_marido = forms.CharField(max_length=80, label="Nome do Marido")
    nome_esposa = forms.CharField(max_length=80, label="Nome da Esposa")
    celular_marido = forms.CharField(max_length=20, required=False, label="Celular do Marido")
    celular_esposa = forms.CharField(max_length=20, required=False, label="Celular da Esposa")

    class Meta:
        model = Casal
        fields = ['nome_marido', 'nome_esposa', 'celular_marido', 'celular_esposa']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if type(field.widget) in (forms.CheckboxInput, forms.RadioSelect):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'


class CasalForm(forms.ModelForm):
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Deixe em branco para manter a senha atual. Para novos usuários, a senha deve ter pelo menos 8 caracteres."
    )

    class Meta:
        model = Casal
        fields = ['username', 'nome_marido', 'nome_esposa', 'celular_marido', 'celular_esposa', 'perfil', 'associado', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if type(field.widget) in (forms.CheckboxInput, forms.RadioSelect):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'
        self.fields['username'].help_text = "Nome de usuário para login"

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user