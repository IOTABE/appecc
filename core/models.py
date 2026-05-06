from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

class Casal(AbstractUser):
    """
    Representa o Casal. Como o ECC trata o casal como uma unidade no encontro,
    estendemos o AbstractUser para gerenciar autenticação usando um email unificado
    ou nome de usuário representativo (ex: joao_maria).
    """
    telefone_marido = models.CharField(max_length=20, blank=True)
    telefone_esposa = models.CharField(max_length=20, blank=True)
    associado = models.BooleanField(default=False, help_text="É um encontreiro associado ativo?")

class FichaInscricao(models.Model):
    casal = models.OneToOneField(Casal, on_delete=models.CASCADE, related_name='ficha_inscricao')
    
    # Dados Profissionais
    profissao_marido = models.CharField(max_length=100)
    profissao_esposa = models.CharField(max_length=100)
    local_trabalho_marido = models.CharField(max_length=150, blank=True)
    local_trabalho_esposa = models.CharField(max_length=150, blank=True)
    
    # Dados Religiosos
    religiao_marido = models.CharField(max_length=50)
    religiao_esposa = models.CharField(max_length=50)
    casados_igreja = models.BooleanField(default=False)
    
    # Dados Médicos (Ficha 43)
    alergias_marido = models.TextField(blank=True, help_text="Especifique alergias alimentares ou a medicamentos.")
    alergias_esposa = models.TextField(blank=True, help_text="Especifique alergias alimentares ou a medicamentos.")
    medicacao_uso_continuo = models.TextField(blank=True)
    restricoes_alimentares = models.TextField(blank=True)
    
    # Dados dos Filhos
    filhos_nomes_idades = models.TextField(blank=True, help_text="Nomes e idades dos filhos.")

class Encontro(models.Model):
    STATUS_CHOICES = [
        ('PLANEJAMENTO', 'Em Planejamento'),
        ('ANDAMENTO', 'Em Andamento'),
        ('FINALIZADO', 'Finalizado'),
    ]
    numero = models.IntegerField(unique=True)
    data_inicio = models.DateField()
    data_fim = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANEJAMENTO')

class FichaConvite(models.Model):
    """Fichas adquiridas por Encontreiros para convidar novos casais."""
    patrocinador = models.ForeignKey(Casal, on_delete=models.PROTECT, related_name='fichas_patrocinadas')
    encontro = models.ForeignKey(Encontro, on_delete=models.CASCADE)
    valor_original = models.DecimalField(max_digits=10, decimal_places=2)
    desconto_aplicado = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    valor_final = models.DecimalField(max_digits=10, decimal_places=2)
    utilizada = models.BooleanField(default=False)

class Circulo(models.Model):
    CORES = [
        ('AMARELO', 'Amarelo'),
        ('AZUL', 'Azul'),
        ('VERDE', 'Verde'),
        ('VERMELHO', 'Vermelho'),
    ]
    encontro = models.ForeignKey(Encontro, on_delete=models.CASCADE, related_name='circulos')
    cor = models.CharField(max_length=10, choices=CORES)
    casal_coordenador = models.ForeignKey(Casal, on_delete=models.SET_NULL, null=True, related_name='circulos_coordenados')
    casais = models.ManyToManyField(Casal, related_name='circulos_participantes', blank=True)

class EquipeTrabalho(models.Model):
    nome = models.CharField(max_length=100) # Ex: Cozinha, Boa Vontade, Liturgia
    encontro = models.ForeignKey(Encontro, on_delete=models.CASCADE, related_name='equipes')
    casais = models.ManyToManyField(Casal, related_name='equipes_trabalho')

# --- ENGINE FINANCEIRA ---

class ContaContabil(models.Model):
    TIPO_CHOICES = [('ATIVO', 'Ativo'), ('PASSIVO', 'Passivo'), ('RECEITA', 'Receita'), ('DESPESA', 'Despesa')]
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)

class MovimentacaoFinanceira(models.Model):
    encontro = models.ForeignKey(Encontro, on_delete=models.PROTECT, related_name='movimentacoes')
    data = models.DateTimeField(auto_now_add=True)
    descricao = models.CharField(max_length=255)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)

class LancamentoContabil(models.Model):
    TIPO_LANCAMENTO = [('D', 'Débito'), ('C', 'Crédito')]
    movimentacao = models.ForeignKey(MovimentacaoFinanceira, on_delete=models.CASCADE, related_name='lancamentos')
    conta = models.ForeignKey(ContaContabil, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=1, choices=TIPO_LANCAMENTO)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
