from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Casal, FichaInscricao, Encontro, FichaConvite,
    Circulo, EquipeTrabalho, ContaContabil,
    MovimentacaoFinanceira, LancamentoContabil,
)


@admin.register(Casal)
class CasalAdmin(UserAdmin):
    """Admin do Casal estendendo o UserAdmin padrão."""
    list_display = ('username', 'nome_marido', 'nome_esposa', 'celular_marido', 'celular_esposa', 'associado')
    list_filter = ('associado', 'is_active')
    search_fields = ('username', 'nome_marido', 'nome_esposa', 'email')
    
    # Adicionar campos personalizados às seções do UserAdmin
    fieldsets = UserAdmin.fieldsets + (
        ('Dados do Casal', {
            'fields': (
                'nome_marido', 'nome_esposa',
                'telefone_marido', 'telefone_esposa',
                'celular_marido', 'celular_esposa',
                'associado',
            ),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Dados do Casal', {
            'fields': (
                'nome_marido', 'nome_esposa',
                'celular_marido', 'celular_esposa',
            ),
        }),
    )


@admin.register(Encontro)
class EncontroAdmin(admin.ModelAdmin):
    list_display = ('numero', 'data_inicio', 'data_fim', 'status', 'total_fichas')
    list_filter = ('status',)
    ordering = ('-numero',)

    def total_fichas(self, obj):
        return obj.fichas_inscricao.count()
    total_fichas.short_description = 'Fichas'


@admin.register(FichaInscricao)
class FichaInscricaoAdmin(admin.ModelAdmin):
    list_display = (
        'numero_ficha', 'encontro', 'get_nome_marido', 'get_nome_esposa',
        'get_cracha_marido', 'get_cracha_esposa', 'data_casamento',
    )
    list_filter = ('encontro', 'casados_civil_religioso')
    search_fields = (
        'casal__nome_marido', 'casal__nome_esposa',
        'nome_cracha_marido', 'nome_cracha_esposa',
    )
    ordering = ('encontro', 'numero_ficha')
    readonly_fields = ('numero_ficha',)

    fieldsets = (
        ('Identificação', {
            'fields': ('encontro', 'casal', 'numero_ficha'),
        }),
        ('Crachá', {
            'fields': ('nome_cracha_marido', 'nome_cracha_esposa'),
        }),
        ('Datas Importantes', {
            'fields': ('data_nascimento_marido', 'data_nascimento_esposa', 'data_casamento'),
        }),
        ('Dados Profissionais', {
            'fields': (
                'profissao_marido', 'profissao_esposa',
                'local_trabalho_marido', 'local_trabalho_esposa',
            ),
        }),
        ('Dados Religiosos', {
            'fields': ('religiao_marido', 'religiao_esposa', 'casados_civil_religioso'),
        }),
        ('Saúde', {
            'fields': (
                'alergias_marido', 'alergias_esposa',
                'medicacao_uso_continuo', 'restricoes_alimentares',
            ),
        }),
        ('Família', {
            'fields': ('qtde_filhos', 'filhos_nomes_idades', 'quem_fica_com_filhos', 'tem_veiculo'),
        }),
        ('Endereço e Contato', {
            'fields': (
                'endereco_rua', 'endereco_numero', 'endereco_bairro',
                'endereco_cep', 'endereco_cidade', 'endereco_uf',
                'telefone_residencial',
            ),
        }),
    )

    def get_nome_marido(self, obj):
        return obj.casal.nome_marido or '-'
    get_nome_marido.short_description = 'Marido'

    def get_nome_esposa(self, obj):
        return obj.casal.nome_esposa or '-'
    get_nome_esposa.short_description = 'Esposa'

    def get_cracha_marido(self, obj):
        return obj.nome_cracha_marido or '-'
    get_cracha_marido.short_description = 'Crachá (Ele)'

    def get_cracha_esposa(self, obj):
        return obj.nome_cracha_esposa or '-'
    get_cracha_esposa.short_description = 'Crachá (Ela)'


@admin.register(FichaConvite)
class FichaConviteAdmin(admin.ModelAdmin):
    list_display = ('patrocinador', 'encontro', 'valor_original', 'desconto_aplicado', 'valor_final', 'utilizada')
    list_filter = ('encontro', 'utilizada')


@admin.register(Circulo)
class CirculoAdmin(admin.ModelAdmin):
    list_display = ('cor', 'encontro', 'casal_coordenador', 'total_casais')
    list_filter = ('encontro', 'cor')
    filter_horizontal = ('casais',)

    def total_casais(self, obj):
        return obj.casais.count()
    total_casais.short_description = 'Casais'


@admin.register(EquipeTrabalho)
class EquipeTrabalhoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'encontro', 'total_casais')
    list_filter = ('encontro',)
    filter_horizontal = ('casais',)

    def total_casais(self, obj):
        return obj.casais.count()
    total_casais.short_description = 'Casais'


@admin.register(ContaContabil)
class ContaContabilAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo')
    list_filter = ('tipo',)


class LancamentoInline(admin.TabularInline):
    model = LancamentoContabil
    extra = 2


@admin.register(MovimentacaoFinanceira)
class MovimentacaoFinanceiraAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'encontro', 'valor_total', 'data')
    list_filter = ('encontro',)
    inlines = [LancamentoInline]
