# SchedCar

Projeto Django de dimensionamento e gestão intregada, para gerenciamento de pedidos e controle de frotas de carros, define os veículos necessários se baseando em quantidade de assentos, automatizando o ciclo de atendimento e reduzindo custos operacionais.

## Contexto do problema

O problema central seria a dificuldade de agendar um carro, como tudo acontece de maneira manual, acaba acontecendo algumas divergencias.

O porto do itaqui possui rotinas que exigem deslocamentos frequentes dos colaboradores. equipes precisam participar de atividades em diferentes áreas.

Frota:

- frota de 8 veiculos
- 2 veiculos com capacidade para 18 passageiros
- 8 com capacidade para 4 passageiros
- veiculos menores atendem reunioes, inspecoes e deslocamentos

Fluxo atual (manual):

- para fazer a solicitacao de um veiculo, o colaborador informa os dados da viagem
- depois disso um profissional do COSEG (setor responsavel), tenta verificar a disponibilidade, selecionar um veiculo adequado e comunicar a demanda a um motorista
- como os registros nao sao centralizados, essa conferencia depende de consultas manuais e de memoria dos envolvidos

## Qual é o principal problema que este software vai resolver?

- Não apresenta informações armazenadas.
- Dificuldade no agendamento.
- Conflito de agendamento.
- Conflito na disponibilidade dos carros.
- Falta de protocolo para comprovar a viagem.
- Falta de comunicação.
- Não apresenta uma segurança efetiva no armazenamentos de informações.

Referências do problema vindas das anotações:

- ao invés de ligar, mandar email, mandar mensagem, a pessoa que irá agendar, reservando o carro em um horario agendado
- no momento em que digitar que todos os veiculos estao ocupados tem que acusar que os veiculos nao estao disponiveis
- é como se fosse uma easy taxi que presta serviço
- agendamentos para colaboradores, não é para o publico, é como se fosse uma empresa terceirizada que é contratada pela empresa

Este projeto foi desenvolvido em Python com Django e inclui funcionalidades básicas de cadastro de marcas e veículos, além de suporte para upload de fotos.

## Requisitos

- Python 3.11+
- pip
- Git
- Ambiente virtual (recomendado)

## Como rodar localmente

### 1) Criar ambiente virtual

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Instalar dependências

```bash
pip install -r requirements.txt
```

### 3) Rodar migrações

```bash
python manage.py migrate
```

### 4) Iniciar o servidor

```bash
python manage.py runserver
```

Depois, abra no navegador:

```text
http://127.0.0.1:8000/
```

Para acessar o painel administrativo:

```text
http://127.0.0.1:8000/admin/
```

## Observações

- O projeto usa SQLite para desenvolvimento.
- As imagens de veículos ficam em `media/cars/`.
- Em desenvolvimento, as notificações ficam no terminal porque o backend de e-mail padrão é o console.
- Para enviar notificações aos gerentes, configure `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` e `EMAIL_USE_TLS` no ambiente, além de cadastrar um e-mail real no usuário com papel de gerente.

## Estrutura principal

- `app/` — configuração do projeto Django
- `cars/` — app com modelos, admin e lógica do domínio
- `manage.py` — comando principal do Django
