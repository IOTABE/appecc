import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

class Casal(AbstractUser):
    """
    Representa o Casal. Como o ECC trata o casal como uma unidade no encontro,
    estendemos o AbstractUser para gerenciar autenticação usando um email unificado
    ou nome de usuário representativo (ex: joao_maria).
    """
    PERFIL_CHOICES = [
        ('', 'Selecione...'),
        ('PRESIDENTE', 'Presidente'),
        ('TESOUREIRO', 'Tesoureiro'),
        ('SECRETARIO', 'Secretário'),
        ('COORDENADOR', 'Coordenador de Encontro'),
        ('OUTROS', 'Outros'),
    ]
    nome_marido = models.CharField(max_length=80, blank=True, verbose_name="Nome do Marido")
    nome_esposa = models.CharField(max_length=80, blank=True, verbose_name="Nome da Esposa")
    telefone_marido = models.CharField(max_length=20, blank=True)
    telefone_esposa = models.CharField(max_length=20, blank=True)
    celular_marido = models.CharField(max_length=20, blank=True, verbose_name="Celular do Marido")
    celular_esposa = models.CharField(max_length=20, blank=True, verbose_name="Celular da Esposa")
    associado = models.BooleanField(default=False, help_text="É um encontreiro associado ativo?")
    perfil = models.CharField(max_length=20, choices=PERFIL_CHOICES, blank=True, verbose_name="Perfil na Diretoria")

    def __str__(self):
        return f"{self.nome_marido} e {self.nome_esposa}"

class FichaInscricao(models.Model):
    """
    Ficha de Inscrição vinculada a um Encontro específico.
    A numeração reinicia a cada encontro (1, 2, 3... sem limite).
    """
    encontro = models.ForeignKey('Encontro', on_delete=models.CASCADE, related_name='fichas_inscricao',
                                 verbose_name="Encontro")
    casal = models.ForeignKey(Casal, on_delete=models.CASCADE, related_name='fichas_inscricao')
    casal_convidou = models.ForeignKey(Casal, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='fichas_convidou', verbose_name="Casal que convidou")
    numero_ficha = models.PositiveIntegerField(verbose_name="Nº da Ficha",
                                               help_text="Numeração sequencial por encontro (começa em 1).")
    ativa = models.BooleanField(default=True, verbose_name="Ficha Ativa",
                               help_text="Desmarque para desabilitar a ficha sem excluí-la.")
    
    # Dados Pessoais / Crachá
    nome_cracha_marido = models.CharField(max_length=80, blank=True, verbose_name="Nome para o Crachá (Marido)",
                                          help_text="Como o marido gostaria de ser chamado durante o encontro.")
    nome_cracha_esposa = models.CharField(max_length=80, blank=True, verbose_name="Nome para o Crachá (Esposa)",
                                          help_text="Como a esposa gostaria de ser chamada durante o encontro.")
    
    # Datas Importantes
    data_nascimento_marido = models.DateField(null=True, blank=True, verbose_name="Data de Nascimento do Marido")
    data_nascimento_esposa = models.DateField(null=True, blank=True, verbose_name="Data de Nascimento da Esposa")
    data_casamento = models.DateField(null=True, blank=True, verbose_name="Data de Casamento")
    
    # Dados Profissionais
    profissao_marido = models.CharField(max_length=100)
    profissao_esposa = models.CharField(max_length=100)
    local_trabalho_marido = models.CharField(max_length=150, blank=True)
    local_trabalho_esposa = models.CharField(max_length=150, blank=True)
    
    # Dados Religiosos
    religiao_marido = models.CharField(max_length=50)
    religiao_esposa = models.CharField(max_length=50)
    casados_civil_religioso = models.BooleanField(default=False, verbose_name="Casados no civil e/ou religioso")
    
    # Dados Médicos (Ficha 43)
    alergias_marido = models.TextField(blank=True, help_text="Especifique alergias alimentares ou a medicamentos.")
    alergias_esposa = models.TextField(blank=True, help_text="Especifique alergias alimentares ou a medicamentos.")
    medicacao_uso_continuo = models.TextField(blank=True)
    restricoes_alimentares = models.TextField(blank=True)
    
    # Dados dos Filhos
    qtde_filhos = models.PositiveIntegerField(default=0, verbose_name="Quantidade de Filhos")
    filhos_nomes_idades = models.TextField(blank=True, help_text="Nomes e idades dos filhos.")
    quem_fica_com_filhos = models.CharField(max_length=150, blank=True, verbose_name="Com quem ficarão os filhos durante o Encontro?")

    # Endereço e Contato
    endereco_rua = models.CharField(max_length=150, blank=True, verbose_name="Rua")
    endereco_numero = models.CharField(max_length=20, blank=True, verbose_name="Número")
    endereco_bairro = models.CharField(max_length=100, blank=True, verbose_name="Bairro")
    endereco_cep = models.CharField(max_length=20, blank=True, verbose_name="CEP")
    endereco_cidade = models.CharField(max_length=100, blank=True, verbose_name="Cidade")
    endereco_uf = models.CharField(max_length=2, blank=True, verbose_name="UF")
    telefone_residencial = models.CharField(max_length=20, blank=True, verbose_name="Telefone Fixo/Residencial")

    # Informações Adicionais
    tem_veiculo = models.BooleanField(default=False, verbose_name="Possui veículo?")

    class Meta:
        unique_together = [
            ('encontro', 'numero_ficha'),  # Número único por encontro
            ('encontro', 'casal'),          # Um casal só pode ter uma ficha por encontro
        ]
        ordering = ['encontro', 'numero_ficha']
        verbose_name = 'Ficha de Inscrição'
        verbose_name_plural = 'Fichas de Inscrição'

    def __str__(self):
        return f"Ficha #{self.numero_ficha} - ECC {self.encontro.numero}"

    def save(self, *args, **kwargs):
        """Auto-numera a ficha se numero_ficha não foi informado."""
        if not self.numero_ficha:
            ultimo = FichaInscricao.objects.filter(
                encontro=self.encontro
            ).order_by('-numero_ficha').values_list('numero_ficha', flat=True).first()
            self.numero_ficha = (ultimo or 0) + 1
        super().save(*args, **kwargs)

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
    valor_inscricao = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Valor da Inscrição")

    def __str__(self):
        return f"{self.numero}º Encontro de Casais com Cristo"

class FichaConvite(models.Model):
    """Fichas adquiridas por Encontreiros para convidar novos casais."""
    patrocinador = models.ForeignKey(Casal, on_delete=models.PROTECT, related_name='fichas_patrocinadas')
    encontro = models.ForeignKey(Encontro, on_delete=models.CASCADE)
    valor_original = models.DecimalField(max_digits=10, decimal_places=2)
    desconto_aplicado = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    valor_final = models.DecimalField(max_digits=10, decimal_places=2)
    utilizada = models.BooleanField(default=False)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    nome_casal_convidado = models.CharField(max_length=150, blank=True, verbose_name="Nome do Casal Convidado")

    def __str__(self):
        return f"Ficha Convite #{self.token}"

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

    def __str__(self):
        return f"Círculo {self.cor} - {self.encontro}"

class EquipeTrabalho(models.Model):
    nome = models.CharField(max_length=100) # Ex: Cozinha, Boa Vontade, Louvor
    encontro = models.ForeignKey(Encontro, on_delete=models.CASCADE, related_name='equipes')
    casais = models.ManyToManyField(Casal, related_name='equipes_trabalho')

    def __str__(self):
        return f"Equipe {self.nome} - {self.encontro}"

# --- ENGINE FINANCEIRA ---

class ContaContabil(models.Model):
    TIPO_CHOICES = [('ATIVO', 'Ativo'), ('PASSIVO', 'Passivo'), ('RECEITA', 'Receita'), ('DESPESA', 'Despesa')]
    NIVEL_CHOICES = [(1, 'Nível 1'), (2, 'Nível 2'), (3, 'Nível 3 - Analítica')]
    NATUREZA_DA_CONTA_CHOICES = [
        ('D', 'Débito'), 
        ('C', 'Crédito')
    ]

    codigo = models.CharField(max_length=20, unique=True, help_text="Código da conta (ex: 1.0.0)")
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    nivel = models.PositiveSmallIntegerField(choices=NIVEL_CHOICES, default=1)
    natureza_da_conta = models.CharField(max_length=10, choices=NATUREZA_DA_CONTA_CHOICES)
    conta_pai = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcontas')

    class Meta:
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.nome}"

    @property
    def e_analitica(self):
        return self.nivel == 3

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.nivel == 1 and self.conta_pai:
            raise ValidationError("Conta de nível 1 não pode ter conta pai.")
        if self.nivel == 2 and not self.conta_pai:
            raise ValidationError("Conta de nível 2 deve ter uma conta pai (nível 1).")
        if self.nivel == 3 and (not self.conta_pai or not self.conta_pai.conta_pai):
            raise ValidationError("Conta de nível 3 deve ter conta pai (nível 2) que pertença a uma conta nível 1.")

class MovimentacaoFinanceira(models.Model):
    encontro = models.ForeignKey(Encontro, on_delete=models.PROTECT, related_name='movimentacoes')
    data = models.DateTimeField(auto_now_add=True)
    descricao = models.CharField(max_length=255)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Movimentação #{self.id} - {self.descricao}"

class LancamentoContabil(models.Model):
    TIPO_LANCAMENTO = [('D', 'Débito'), ('C', 'Crédito')]
    movimentacao = models.ForeignKey(MovimentacaoFinanceira, on_delete=models.CASCADE, related_name='lancamentos')
    conta = models.ForeignKey(ContaContabil, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=1, choices=TIPO_LANCAMENTO)
    valor = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Lançamento #{self.id} - {self.tipo} {self.valor}"
