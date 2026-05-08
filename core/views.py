from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.views import View
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.contrib import messages

from .models import (
    Encontro, EquipeTrabalho, Circulo, MovimentacaoFinanceira,
    LancamentoContabil, FichaInscricao, ContaContabil, Casal, FichaConvite
)
from .forms import (
    FichaInscricaoForm, EncontroForm, MovimentacaoForm,
    ContaContabilForm, LancamentoContabilFormSet, CasalForm, ConviteRegistroForm
)


def pode_gerenciar_fichas(user):
    """Verifica se o usuário pode gerenciar fichas e encontros."""
    if user.is_superuser:
        return True
    if not hasattr(user, 'perfil') or not user.perfil:
        return False
    return user.perfil in ['PRESIDENTE', 'TESOUREIRO', 'SECRETARIO', 'COORDENADOR']


def perfil_tesoureiro_ou_presidente(user):
    """Verifica se o usuário é presidente, tesoureiro ou superuser."""
    if user.is_superuser:
        return True
    if not hasattr(user, 'perfil') or not user.perfil:
        return False
    return user.perfil in ['PRESIDENTE', 'TESOUREIRO']


def login_required_tesoureiro(view_func):
    """Decorator que exige perfil de tesoureiro ou presidente."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin:login')
        if not perfil_tesoureiro_ou_presidente(request.user):
            messages.error(request, 'Acesso restrito: apenas tesoureiro ou presidente.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def login_required_gerenciar(view_func):
    """Decorator que exige perfil para gerenciar fichas/encontros."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not pode_gerenciar_fichas(request.user):
            messages.error(request, 'Acesso restrito.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def _get_encontro_ativo():
    """Retorna o encontro em planejamento ou andamento mais próximo."""
    return Encontro.objects.filter(
        status__in=['PLANEJAMENTO', 'ANDAMENTO']
    ).order_by('data_inicio').first()


def login_required_superuser(view_func):
    """Decorator que exige superuser."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin:login')
        if not request.user.is_superuser:
            messages.error(request, 'Acesso restrito: apenas administradores.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


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


@method_decorator(login_required_gerenciar, name='dispatch')
class FichaListView(View):
    """Lista todas as fichas do encontro ativo."""
    def get(self, request):
        encontro = _get_encontro_ativo()
        fichas = []
        total_ativas = 0
        total_inativas = 0

        if encontro:
            fichas = FichaInscricao.objects.filter(
                encontro=encontro
            ).select_related('casal').order_by('numero_ficha')
            total_ativas = fichas.filter(ativa=True).count()
            total_inativas = fichas.filter(ativa=False).count()

        return render(request, 'ficha_list.html', {
            'encontro': encontro,
            'fichas': fichas,
            'total_ativas': total_ativas,
            'total_inativas': total_inativas,
            'pode_gerenciar': pode_gerenciar_fichas(request.user),
        })


import uuid

@method_decorator(login_required_gerenciar, name='dispatch')
class FichaCreateView(View):
    """Cria uma nova ficha de inscrição."""
    def get(self, request):
        encontro = _get_encontro_ativo()
        form = FichaInscricaoForm(casal=None)
        return render(request, 'ficha_form.html', {
            'form': form,
            'encontro': encontro,
            'ficha': None,
            'is_new': True,
        })

    def post(self, request):
        encontro = _get_encontro_ativo()
        if not encontro:
            return redirect('ficha_list')

        form = FichaInscricaoForm(request.POST, casal=None)
        if form.is_valid():
            nova_ficha = form.save(commit=False)
            nova_ficha.encontro = encontro
            
            # Criar um novo Casal no sistema para esta ficha
            from .models import Casal
            nome_m = form.cleaned_data.get('nome_marido', '').strip() or 'marido'
            nome_e = form.cleaned_data.get('nome_esposa', '').strip() or 'esposa'
            username_base = f"{nome_m.split()[0].lower()}_{nome_e.split()[0].lower()}_{uuid.uuid4().hex[:6]}"
            
            novo_casal = Casal.objects.create(
                username=username_base,
                nome_marido=form.cleaned_data.get('nome_marido', ''),
                nome_esposa=form.cleaned_data.get('nome_esposa', ''),
                celular_marido=form.cleaned_data.get('celular_marido', ''),
                celular_esposa=form.cleaned_data.get('celular_esposa', ''),
            )
            novo_casal.set_unusable_password()  # Eles ainda não tem senha de acesso
            novo_casal.save()

            nova_ficha.casal = novo_casal
            nova_ficha.save()
            return redirect('ficha_list')

        return render(request, 'ficha_form.html', {
            'form': form,
            'encontro': encontro,
            'ficha': None,
            'is_new': True,
        })


@method_decorator(login_required_gerenciar, name='dispatch')
class FichaEditView(View):
    """Edita uma ficha existente."""
    def get(self, request, pk):
        ficha = get_object_or_404(FichaInscricao, pk=pk)
        form = FichaInscricaoForm(instance=ficha, casal=ficha.casal)
        return render(request, 'ficha_form.html', {
            'form': form,
            'encontro': ficha.encontro,
            'ficha': ficha,
            'is_new': False,
        })

    def post(self, request, pk):
        ficha = get_object_or_404(FichaInscricao, pk=pk)
        form = FichaInscricaoForm(request.POST, instance=ficha, casal=ficha.casal)
        if form.is_valid():
            form.save()
            form.save_casal_fields()
            return redirect('ficha_list')

        return render(request, 'ficha_form.html', {
            'form': form,
            'encontro': ficha.encontro,
            'ficha': ficha,
            'is_new': False,
        })


@method_decorator(login_required, name='dispatch')
class FichaToggleAtivaView(View):
    """Alterna o status ativa/inativa de uma ficha."""
    def post(self, request, pk):
        ficha = get_object_or_404(FichaInscricao, pk=pk)
        ficha.ativa = not ficha.ativa
        ficha.save(update_fields=['ativa'])
        return redirect('ficha_list')


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


@method_decorator(login_required_gerenciar, name='dispatch')
class EncontroListView(View):
    """Lista todos os encontros."""
    def get(self, request):
        encontros = Encontro.objects.order_by('-numero')
        pode_gerenciar_var = pode_gerenciar_fichas(request.user)
        return render(request, 'encontro_list.html', {
            'encontros': encontros,
            'pode_gerenciar': pode_gerenciar_var,
        })


@method_decorator(login_required_gerenciar, name='dispatch')
class EncontroCreateView(View):
    """Cria um novo encontro."""
    def get(self, request):
        form = EncontroForm()
        return render(request, 'encontro_form.html', {'form': form, 'encontro': None, 'is_new': True})

    def post(self, request):
        form = EncontroForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('encontro_list')
        return render(request, 'encontro_form.html', {'form': form, 'encontro': None, 'is_new': True})


@method_decorator(login_required_gerenciar, name='dispatch')
class EncontroEditView(View):
    """Edita um encontro existente."""
    def get(self, request, pk):
        encontro = get_object_or_404(Encontro, pk=pk)
        form = EncontroForm(instance=encontro)
        return render(request, 'encontro_form.html', {'form': form, 'encontro': encontro, 'is_new': False})

    def post(self, request, pk):
        encontro = get_object_or_404(Encontro, pk=pk)
        form = EncontroForm(request.POST, instance=encontro)
        if form.is_valid():
            form.save()
            return redirect('encontro_list')
        return render(request, 'encontro_form.html', {'form': form, 'encontro': encontro, 'is_new': False})


@method_decorator(login_required_gerenciar, name='dispatch')
class EncontroDeleteView(View):
    """Exclui um encontro (apenas se não tiver fichas)."""
    def get(self, request, pk):
        encontro = get_object_or_404(Encontro, pk=pk)
        if encontro.fichas_inscricao.exists():
            return render(request, 'encontro_list.html', {
                'encontros': Encontro.objects.order_by('-numero'),
                'pode_gerenciar': pode_gerenciar_fichas(request.user),
                'error': 'Não é possível excluir encontro com fichas inscritas.'
            })
        return render(request, 'encontro_confirm_delete.html', {'encontro': encontro})

    def post(self, request, pk):
        encontro = get_object_or_404(Encontro, pk=pk)
        if encontro.fichas_inscricao.exists():
            return redirect('encontro_list')
        encontro.delete()
        return redirect('encontro_list')


@method_decorator(login_required_gerenciar, name='dispatch')
class UsuarioDeleteView(View):
    """Exclui usuário."""
    def get(self, request, pk):
        casal = get_object_or_404(Casal, pk=pk)
        if casal == request.user:
            messages.error(request, 'Você não pode excluir seu próprio usuário.')
            return redirect('usuario_list')
        return render(request, 'usuario_confirm_delete.html', {'casal': casal})

    def post(self, request, pk):
        casal = get_object_or_404(Casal, pk=pk)
        if casal == request.user:
            messages.error(request, 'Você não pode excluir seu próprio usuário.')
            return redirect('usuario_list')
        casal.delete()
        return redirect('usuario_list')


@method_decorator(login_required, name='dispatch')
class ConviteListView(View):
    """Lista e gera links de convite."""
    def get(self, request):
        fichas = FichaConvite.objects.filter(patrocinador=request.user).order_by('-id')
        encontros = Encontro.objects.filter(status__in=['PLANEJAMENTO', 'ANDAMENTO']).order_by('-numero')
        return render(request, 'convite_list.html', {'fichas': fichas, 'encontros': encontros})

    def post(self, request):
        encontro_id = request.POST.get('encontro')
        nome_casal = request.POST.get('nome_casal', '')
        encontro = get_object_or_404(Encontro, pk=encontro_id)

        ficha = FichaConvite.objects.create(
            patrocinador=request.user,
            encontro=encontro,
            valor_original=getattr(encontro, 'valor_inscricao', 0) or 0,
            desconto_aplicado=0,
            valor_final=getattr(encontro, 'valor_inscricao', 0) or 0,
            nome_casal_convidado=nome_casal,
        )
        link = request.build_absolute_uri(f'/convite/{ficha.token}/')
        encontros = Encontro.objects.filter(status__in=['PLANEJAMENTO', 'ANDAMENTO']).order_by('-numero')
        return render(request, 'convite_list.html', {
            'fichas': FichaConvite.objects.filter(patrocinador=request.user).order_by('-id'),
            'encontros': encontros,
            'link_gerado': link,
        })


@method_decorator(login_required, name='dispatch')
class ConviteDeleteView(View):
    """Exclui um convite não utilizado."""
    def post(self, request, pk):
        ficha = get_object_or_404(FichaConvite, pk=pk, patrocinador=request.user)
        if not ficha.utilizada:
            ficha.delete()
        return redirect('convite_list')


class ConviteRegistroView(View):
    """Página de registro via convite com ficha completa."""
    def get(self, request, token):
        ficha = get_object_or_404(FichaConvite, token=token)
        if ficha.utilizada:
            return render(request, 'convite_erro.html', {'mensagem': 'Este convite já foi utilizado.'})

        form = FichaInscricaoForm(casal=None)
        return render(request, 'convite_registro.html', {
            'ficha': ficha,
            'form': form,
            'patrocinador': ficha.patrocinador,
            'is_new': True,
        })

    def post(self, request, token):
        ficha = get_object_or_404(FichaConvite, token=token)
        if ficha.utilizada:
            return render(request, 'convite_erro.html', {'mensagem': 'Este convite já foi utilizado.'})

        form = FichaInscricaoForm(request.POST, casal=None)
        if form.is_valid():
            import uuid
            nome_m = form.cleaned_data.get('nome_marido', '').strip() or 'marido'
            nome_e = form.cleaned_data.get('nome_esposa', '').strip() or 'esposa'
            username_base = f"{nome_m.split()[0].lower()}_{nome_e.split()[0].lower()}_{uuid.uuid4().hex[:6]}"

            novo_casal = Casal.objects.create(
                username=username_base,
                nome_marido=form.cleaned_data.get('nome_marido', ''),
                nome_esposa=form.cleaned_data.get('nome_esposa', ''),
                celular_marido=form.cleaned_data.get('celular_marido', ''),
                celular_esposa=form.cleaned_data.get('celular_esposa', ''),
            )
            novo_casal.set_unusable_password()
            novo_casal.save()

            ficha_inscricao = FichaInscricao(
                encontro=ficha.encontro,
                casal=novo_casal,
                casal_convidou=ficha.patrocinador,
            )
            for field in form.cleaned_data:
                if hasattr(ficha_inscricao, field):
                    setattr(ficha_inscricao, field, form.cleaned_data[field])
            ficha_inscricao.save()

            ficha.utilizada = True
            ficha.save()

            return render(request, 'convite_sucesso.html', {'casal': novo_casal})

        return render(request, 'convite_registro.html', {
            'ficha': ficha,
            'form': form,
            'patrocinador': ficha.patrocinador,
            'is_new': True,
        })

    def post(self, request, token):
        ficha = get_object_or_404(FichaConvite, token=token)
        if ficha.utilizada:
            return render(request, 'convite_erro.html', {'mensagem': 'Este convite já foi utilizado.'})

        form = FichaInscricaoForm(request.POST, casal=None)
        if form.is_valid():
            import uuid
            nome_m = form.cleaned_data.get('nome_marido', '').strip() or 'marido'
            nome_e = form.cleaned_data.get('nome_esposa', '').strip() or 'esposa'
            username_base = f"{nome_m.split()[0].lower()}_{nome_e.split()[0].lower()}_{uuid.uuid4().hex[:6]}"

            novo_casal = Casal.objects.create(
                username=username_base,
                nome_marido=form.cleaned_data.get('nome_marido', ''),
                nome_esposa=form.cleaned_data.get('nome_esposa', ''),
                celular_marido=form.cleaned_data.get('celular_marido', ''),
                celular_esposa=form.cleaned_data.get('celular_esposa', ''),
            )
            novo_casal.set_unusable_password()
            novo_casal.save()

            ficha_inscricao = form.save(commit=False)
            ficha_inscricao.encontro = ficha.encontro
            ficha_inscricao.casal = novo_casal
            ficha_inscricao.casal_convidou = ficha.patrocinador
            ficha_inscricao.save()

            ficha.utilizada = True
            ficha.save()

            return render(request, 'convite_sucesso.html', {'casal': novo_casal})

        return render(request, 'convite_registro.html', {
            'ficha': ficha,
            'form': form,
            'patrocinador': ficha.patrocinador,
            'is_new': True,
        })


@method_decorator(login_required_tesoureiro, name='dispatch')
class FinanceiroListView(View):
    """Lista movimentações financeiras (apenas tesoureiro/presidente)."""
    def get(self, request):
        encontro_id = request.GET.get('encontro')
        if encontro_id:
            movimentacoes = MovimentacaoFinanceira.objects.filter(encontro_id=encontro_id).order_by('-data')
            encontro_selecionado = get_object_or_404(Encontro, pk=encontro_id)
        else:
            movimentacoes = MovimentacaoFinanceira.objects.order_by('-data')[:50]
            encontro_selecionado = None

        encontros = Encontro.objects.order_by('-numero')
        return render(request, 'financeiro_list.html', {
            'movimentacoes': movimentacoes,
            'encontros': encontros,
            'encontro_selecionado': encontro_selecionado,
        })


@method_decorator(login_required_tesoureiro, name='dispatch')
class FinanceiroCreateView(View):
    """Cria nova movimentação com lançamentos contábeis."""
    def get(self, request):
        form = MovimentacaoForm()
        formset = LancamentoContabilFormSet()
        return render(request, 'financeiro_form.html', {
            'form': form, 'formset': formset, 'movimentacao': None, 'is_new': True
        })

    def post(self, request):
        form = MovimentacaoForm(request.POST)
        formset = LancamentoContabilFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            movimentacao = form.save()
            formset.instance = movimentacao
            formset.save()
            return redirect('financeiro_list')
        return render(request, 'financeiro_form.html', {
            'form': form, 'formset': formset, 'movimentacao': None, 'is_new': True
        })


@method_decorator(login_required_tesoureiro, name='dispatch')
class FinanceiroEditView(View):
    """Edita uma movimentação."""
    def get(self, request, pk):
        movimentacao = get_object_or_404(MovimentacaoFinanceira, pk=pk)
        form = MovimentacaoForm(instance=movimentacao)
        formset = LancamentoContabilFormSet(instance=movimentacao)
        return render(request, 'financeiro_form.html', {
            'form': form, 'formset': formset, 'movimentacao': movimentacao, 'is_new': False
        })

    def post(self, request, pk):
        movimentacao = get_object_or_404(MovimentacaoFinanceira, pk=pk)
        form = MovimentacaoForm(request.POST, instance=movimentacao)
        formset = LancamentoContabilFormSet(request.POST, instance=movimentacao)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect('financeiro_list')
        return render(request, 'financeiro_form.html', {
            'form': form, 'formset': formset, 'movimentacao': movimentacao, 'is_new': False
        })


@method_decorator(login_required_tesoureiro, name='dispatch')
class FinanceiroDeleteView(View):
    """Exclui uma movimentação."""
    def get(self, request, pk):
        movimentacao = get_object_or_404(MovimentacaoFinanceira, pk=pk)
        return render(request, 'financeiro_confirm_delete.html', {'movimentacao': movimentacao})

    def post(self, request, pk):
        movimentacao = get_object_or_404(MovimentacaoFinanceira, pk=pk)
        movimentacao.delete()
        return redirect('financeiro_list')


@method_decorator(login_required_tesoureiro, name='dispatch')
class ContaContabilListView(View):
    """Lista contas contábeis."""
    def get(self, request):
        contas = ContaContabil.objects.order_by('tipo', 'codigo')
        contas_agrupadas = {}
        for conta in contas:
            if conta.tipo not in contas_agrupadas:
                contas_agrupadas[conta.tipo] = []
            contas_agrupadas[conta.tipo].append(conta)
        return render(request, 'conta_list.html', {'contas_agrupadas': contas_agrupadas})


@method_decorator(login_required_tesoureiro, name='dispatch')
class ContaContabilCreateView(View):
    """Cria nova conta contábil."""
    def get(self, request):
        form = ContaContabilForm()
        return render(request, 'conta_form.html', {'form': form, 'conta': None, 'is_new': True})

    def post(self, request):
        form = ContaContabilForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('conta_list')
        return render(request, 'conta_form.html', {'form': form, 'conta': None, 'is_new': True})


@method_decorator(login_required_tesoureiro, name='dispatch')
class ContaContabilEditView(View):
    """Edita conta contábil."""
    def get(self, request, pk):
        conta = get_object_or_404(ContaContabil, pk=pk)
        form = ContaContabilForm(instance=conta)
        return render(request, 'conta_form.html', {'form': form, 'conta': conta, 'is_new': False})

    def post(self, request, pk):
        conta = get_object_or_404(ContaContabil, pk=pk)
        form = ContaContabilForm(request.POST, instance=conta)
        if form.is_valid():
            form.save()
            return redirect('conta_list')
        return render(request, 'conta_form.html', {'form': form, 'conta': conta, 'is_new': False})


@method_decorator(login_required_superuser, name='dispatch')
class UsuarioListView(View):
    """Lista todos os usuários (casais)."""
    def get(self, request):
        casais = Casal.objects.order_by('username')
        return render(request, 'usuario_list.html', {'casais': casais})


@method_decorator(login_required_superuser, name='dispatch')
class UsuarioCreateView(View):
    """Cria novo usuário."""
    def get(self, request):
        form = CasalForm()
        return render(request, 'usuario_form.html', {'form': form, 'casal': None, 'is_new': True})

    def post(self, request):
        form = CasalForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('usuario_list')
        return render(request, 'usuario_form.html', {'form': form, 'casal': None, 'is_new': True})


@method_decorator(login_required_superuser, name='dispatch')
class UsuarioEditView(View):
    """Edita usuário existente."""
    def get(self, request, pk):
        casal = get_object_or_404(Casal, pk=pk)
        form = CasalForm(instance=casal)
        return render(request, 'usuario_form.html', {'form': form, 'casal': casal, 'is_new': False})

    def post(self, request, pk):
        casal = get_object_or_404(Casal, pk=pk)
        form = CasalForm(request.POST, instance=casal)
        if form.is_valid():
            form.save()
            return redirect('usuario_list')
        return render(request, 'usuario_form.html', {'form': form, 'casal': casal, 'is_new': False})


@method_decorator(login_required_superuser, name='dispatch')
class UsuarioDeleteView(View):
    """Exclui usuário."""
    def get(self, request, pk):
        casal = get_object_or_404(Casal, pk=pk)
        if casal == request.user:
            messages.error(request, 'Você não pode excluir seu próprio usuário.')
            return redirect('usuario_list')
        return render(request, 'usuario_confirm_delete.html', {'casal': casal})

    def post(self, request, pk):
        casal = get_object_or_404(Casal, pk=pk)
        if casal == request.user:
            messages.error(request, 'Você não pode excluir seu próprio usuário.')
            return redirect('usuario_list')
        casal.delete()
        return redirect('usuario_list')
