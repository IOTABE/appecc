from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.views import View
from django.utils.decorators import method_decorator

from .models import Encontro, EquipeTrabalho, Circulo, MovimentacaoFinanceira, LancamentoContabil, FichaInscricao
from .forms import FichaInscricaoForm

class HomeView(View):
    def get(self, request):
        proximo_encontro = Encontro.objects.filter(status__in=['PLANEJAMENTO', 'ANDAMENTO']).order_by('data_inicio').first()
        
        if request.user.is_authenticated:
            return self.render_dashboard(request, proximo_encontro)
        else:
            return render(request, 'landing.html', {'encontro': proximo_encontro})
            
    def render_dashboard(self, request, encontro):
        context = {'encontro': encontro}
        
        if encontro:
            # Total de Encontristas por Círculo
            circulos_data = Circulo.objects.filter(encontro=encontro).annotate(total_casais=Count('casais')).values('cor', 'total_casais').order_by('cor')
            context['circulos_data'] = list(circulos_data)
            
            # Total de Encontreiros por Equipe
            equipes_data = EquipeTrabalho.objects.filter(encontro=encontro).annotate(total_casais=Count('casais')).values('nome', 'total_casais').order_by('-total_casais')
            context['equipes_data'] = list(equipes_data)
            
            # Resumo financeiro (Receitas e Despesas do Encontro)
            receitas = LancamentoContabil.objects.filter(
                movimentacao__encontro=encontro, conta__tipo='RECEITA'
            ).aggregate(total=Sum('valor'))['total'] or 0
            
            despesas = LancamentoContabil.objects.filter(
                movimentacao__encontro=encontro, conta__tipo='DESPESA'
            ).aggregate(total=Sum('valor'))['total'] or 0
            
            context['financeiro'] = {
                'receitas': receitas,
                'despesas': despesas,
                'saldo': receitas - despesas
            }
            
        return render(request, 'dashboard.html', context)

@method_decorator(login_required, name='dispatch')
class FichaInscricaoView(View):
    def get(self, request):
        try:
            ficha = request.user.ficha_inscricao
        except FichaInscricao.DoesNotExist:
            ficha = None
            
        form = FichaInscricaoForm(instance=ficha)
        return render(request, 'ficha_form.html', {'form': form})
        
    def post(self, request):
        try:
            ficha = request.user.ficha_inscricao
        except FichaInscricao.DoesNotExist:
            ficha = None
            
        form = FichaInscricaoForm(request.POST, instance=ficha)
        if form.is_valid():
            nova_ficha = form.save(commit=False)
            nova_ficha.casal = request.user
            nova_ficha.save()
            return redirect('home')
            
        return render(request, 'ficha_form.html', {'form': form})

@method_decorator(login_required, name='dispatch')
class BalanceteView(View):
    def get(self, request):
        # Balancete Mensal Simplificado
        balancete = (
            LancamentoContabil.objects
            .annotate(mes=TruncMonth('movimentacao__data'))
            .values('mes', 'conta__tipo')
            .annotate(total=Sum('valor'))
            .order_by('-mes')
        )
        
        # Estruturar para o template
        meses = {}
        for item in balancete:
            mes_str = item['mes'].strftime('%m/%Y') if item['mes'] else 'Desconhecido'
            if mes_str not in meses:
                meses[mes_str] = {'RECEITA': 0, 'DESPESA': 0, 'ATIVO': 0, 'PASSIVO': 0}
            tipo = item['conta__tipo']
            meses[mes_str][tipo] = item['total']
            
        for mes, dados in meses.items():
            dados['saldo'] = dados['RECEITA'] - dados['DESPESA']
            
        return render(request, 'balancete.html', {'meses': meses})
