from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Sum
from .models import Encontro, MovimentacaoFinanceira, LancamentoContabil, FichaConvite, Casal

class EncontroService:
    @staticmethod
    @transaction.atomic
    def finalizar_encontro(encontro_id: int) -> Encontro:
        """
        Máquina de estado: Transita o encontro para 'FINALIZADO'.
        Pode engatilhar rotinas como bloqueio de novas movimentações financeiras.
        """
        encontro = Encontro.objects.select_for_update().get(id=encontro_id)
        
        if encontro.status == 'FINALIZADO':
            raise ValidationError("Este encontro já está finalizado.")
            
        # Regras de validação antes de fechar (ex: verificar se todas as contas batem)
        FinanceiroService.validar_integridade_encontro(encontro)
        
        encontro.status = 'FINALIZADO'
        encontro.save()
        return encontro

class FichaConviteService:
    @staticmethod
    @transaction.atomic
    def gerar_ficha_patrocinada(patrocinador: Casal, encontro: Encontro, valor_base: float, percentual_desconto: float) -> FichaConvite:
        """
        Aplica o sistema de descontos para Encontreiros Associados.
        """
        if not patrocinador.associado:
            raise ValidationError("Apenas encontreiros associados podem patrocinar fichas com desconto.")
            
        if percentual_desconto < 0 or percentual_desconto > 100:
            raise ValidationError("Desconto inválido.")

        valor_desconto = (valor_base * percentual_desconto) / 100
        valor_final = valor_base - valor_desconto

        ficha = FichaConvite.objects.create(
            patrocinador=patrocinador,
            encontro=encontro,
            valor_original=valor_base,
            desconto_aplicado=valor_desconto,
            valor_final=valor_final
        )
        return ficha

class FinanceiroService:
    @staticmethod
    @transaction.atomic
    def registrar_partida_dobrada(encontro: Encontro, descricao: str, valor: float, conta_debito, conta_credito) -> MovimentacaoFinanceira:
        """
        Engine Financeira: Garante a integridade lançando Débito e Crédito simultaneamente.
        """
        movimentacao = MovimentacaoFinanceira.objects.create(
            encontro=encontro,
            descricao=descricao,
            valor_total=valor
        )

        # Lançamento a Débito (Onde o recurso foi aplicado / Destino)
        LancamentoContabil.objects.create(
            movimentacao=movimentacao,
            conta=conta_debito,
            tipo='D',
            valor=valor
        )

        # Lançamento a Crédito (De onde o recurso saiu / Origem)
        LancamentoContabil.objects.create(
            movimentacao=movimentacao,
            conta=conta_credito,
            tipo='C',
            valor=valor
        )

        # Asserção de Integridade imediata
        FinanceiroService._validar_partidas_dobradas(movimentacao)
        
        return movimentacao

    @staticmethod
    def _validar_partidas_dobradas(movimentacao: MovimentacaoFinanceira):
        debitos = movimentacao.lancamentos.filter(tipo='D').aggregate(Sum('valor'))['valor__sum'] or 0
        creditos = movimentacao.lancamentos.filter(tipo='C').aggregate(Sum('valor'))['valor__sum'] or 0
        
        if debitos != creditos:
            raise ValidationError(f"Integridade violada na Movimentacao {movimentacao.id}: Débitos ({debitos}) != Créditos ({creditos})")

    @staticmethod
    def validar_integridade_encontro(encontro: Encontro):
        # Valida todos os lançamentos do encontro antes do fechamento
        for mov in encontro.movimentacoes.all():
            FinanceiroService._validar_partidas_dobradas(mov)
