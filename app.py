# Importa as dependências do aplicativo
from flask import Flask, abort, g, make_response, redirect, render_template, request, url_for
from flask_mysqldb import MySQL
import json
from functions.geral import calcular_idade, datetime_para_string, gerar_senha, remove_prefixo


# Cria um aplicativo Flask chamado "app"
app = Flask(__name__)

# Configurações de acesso ao MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'crudtrecos'

# Setup da conexão com MySQL
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['MYSQL_USE_UNICODE'] = True
app.config['MYSQL_CHARSET'] = 'utf8mb4'

# Variável de conexão com o MySQL
mysql = MySQL(app)


@app.before_request
def start():

    # Setup do MySQL para corrigir acentuação
    cur = mysql.connection.cursor()
    cur.execute("SET NAMES utf8mb4")
    cur.execute("SET character_set_connection=utf8mb4")
    cur.execute("SET character_set_client=utf8mb4")
    cur.execute("SET character_set_results=utf8mb4")

    # Setup do MySQL para dias da semana e meses em português
    cur.execute("SET lc_time_names = 'pt_BR'")

    # Lê o cookie do usuário → 'usuario'
    cookie = request.cookies.get('usuario')

    if cookie:
        # Se o cookie existe
        # Converte o cookie JSON para um dicionário Python
        g.usuario = json.loads(cookie)
    else:
        # Se o cookie não existe, a variável do ususário está vazia
        g.usuario = ''

    # # Cria um usuário "fake" para testes
    # # No futuro, isso virá de um cookie
    # g.usuario = {
    #     'id': '1',
    #     'nome': 'Joca da Silva',
    #     'pnome': 'Joca',
    # }


@app.route("/")
def index():
    if g.usuario == '':
        return redirect(url_for('login'))

    acao = request.args.get('a')

    sql = '''
        SELECT a_id, a_foto, a_nome, a_descricao, a_localizacao, a_material, a_tipo
        FROM acessorio
        WHERE a_usuario = %s
            AND a_status = 'on'
        ORDER BY a_data DESC
    '''
    cur = mysql.connection.cursor()
    cur.execute(sql, (g.usuario['id'],))
    acessorios = cur.fetchall()
    cur.close()

    pagina = {
        'titulo': 'Acessórios Afro - Loja Virtual',
        'usuario': g.usuario,
        'acessorios': acessorios,
        'acao': acao,
    }

    return render_template('index.html', **pagina)



# Rota para a página de cadastro de novo treco
@app.route('/novo', methods=['GET', 'POST'])
def novo():
    if g.usuario == '':
        return redirect(url_for('login'))

    sucesso = False

    if request.method == 'POST':
        form = dict(request.form)

        sql = '''
            INSERT INTO acessorio (
                a_usuario, a_foto, a_nome, a_descricao, a_localizacao, a_material, a_tipo
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        '''
        cur = mysql.connection.cursor()
        cur.execute(sql, (
            g.usuario['id'],
            form['foto'],
            form['nome'],
            form['descricao'],
            form['localizacao'],
            form['material'],
            form['tipo'],
        ))
        mysql.connection.commit()
        cur.close()

        sucesso = True

    pagina = {
        'titulo': 'Acessórios Afro - Novo Acessório',
        'usuario': g.usuario,
        'sucesso': sucesso,
    }

    return render_template('novo.html', **pagina)



@app.route('/edita/<id>', methods=['GET', 'POST'])
def edita(id):
    if g.usuario == '':
        return redirect(url_for('login'))

    if request.method == 'POST':
        form = dict(request.form)

        sql = '''
            UPDATE acessorio 
            SET a_foto = %s,
                a_nome = %s,
                a_descricao = %s,
                a_localizacao = %s,
                a_material = %s,
                a_tipo = %s
            WHERE a_id = %s
        '''
        cur = mysql.connection.cursor()
        cur.execute(sql, (
            form['foto'],
            form['nome'],
            form['descricao'],
            form['localizacao'],
            form['material'],
            form['tipo'],
            id,
        ))
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('index', a='editado'))

    sql = '''
        SELECT * FROM acessorio
        WHERE a_id = %s
            AND a_usuario = %s
            AND a_status = 'on'
    '''
    cur = mysql.connection.cursor()
    cur.execute(sql, (id, g.usuario['id'],))
    row = cur.fetchone()
    cur.close()

    if row == None:
        abort(404)

    pagina = {
        'titulo': 'Acessórios Afro - Editar Acessório',
        'usuario': g.usuario,
        'acessorio': row,
    }

    return render_template('edita.html', **pagina)



@app.route('/apaga/<id>')
def apaga(id):

    # Se o usuário não está logado redireciona para a página de login
    if g.usuario == '':
        return redirect(url_for('login'))

    # (des)comente o método para apagar conforme o seu caso
    # sql = 'DELETE FROM treco WHERE t_id = %s' # Apaga completamente o treco (CUIDADO!)
    # Altera o status do treco para 'del'
    sql = "UPDATE treco SET t_status = 'del'  WHERE t_id = %s"

    # Executa o SQL
    cur = mysql.connection.cursor()
    cur.execute(sql, (id,))
    mysql.connection.commit()
    cur.close()

    # Retorna para a página anterior
    return redirect(url_for('index', a='apagado'))


@app.route('/login', methods=['GET', 'POST'])  # Rota para login de usuário
def login():

    # Verifica se o usuário está logado → Pelo cookie
    if g.usuario != '':
        # Se o usuário está logado
        # Redireciona para a página inicial
        return redirect(url_for('index'))

    erro = False

    if request.method == 'POST':
        # Se o formulário foi enviado

        # Pega os dados preenchidos no formulário
        form = dict(request.form)

        # Teste mesa
        # print('\n\n\nFORM:', form, '\n\n\n')

        # Pesquisa se os dados existem no banco de dados → usuario
        # datetime.datetime(2024, 11, 8, 9, 23, 28)
        sql = '''
            SELECT *,
                -- Gera uma versão das datas em pt-BR
                DATE_FORMAT(u_data, '%%d/%%m/%%Y às %%H:%%m') AS u_databr,
                DATE_FORMAT(u_nascimento, '%%d/%%m/%%Y') AS u_nascimentobr
            FROM usuario
            WHERE u_email = %s
                AND u_senha = SHA1(%s)
                AND u_status = 'on'
        '''
        cur = mysql.connection.cursor()
        cur.execute(sql, (form['email'], form['senha'],))
        usuario = cur.fetchone()
        cur.close()

        # Teste mesa
        # print('\n\n\nDICT:', usuario, '\n\n\n')

        if usuario == None:
            # Se o usuário não foi encontrado
            erro = True
        else:
            # Se achou o usuário
            # Apaga a senha do usuário para salvar no cookie
            del usuario['u_senha']

            # Primeiro nome do usuário
            usuario['u_pnome'] = usuario['u_nome'].split()[0]

            # Formata as datas para usar no JSON
            usuario = datetime_para_string(usuario)

            # Remove o prefixo das chaves do dicionário
            cookie_valor = remove_prefixo(usuario)

            # Converte os dados em JSON (texto) para gravar no cookie
            # Porque cookies só aceitam dados na forma de JSON
            cookie_json = json.dumps(cookie_valor)

            # Teste de mesa
            # print('\n\n\nCOOKIE:', cookie_json, '\n\n\n')

            # Prepara a página de destino → index
            resposta = make_response(redirect(url_for('index')))

            # Cria um cookie
            resposta.set_cookie(
                key='usuario',  # Nome do cookie
                value=cookie_json,  # Valor a ser gravado no cookie
                max_age=60 * 60 * 24 * 365  # Validade do cookie em segundos
            )

            # Redireciona para a página de destino → index
            return resposta

    # Dados, variáveis e valores a serem passados para o template HTML
    pagina = {
        'titulo': 'Acessorios Afro - Login',
        'erro': erro
    }

    return render_template('login.html', **pagina)


@app.route('/logout')
def logout():

    # Se o usuário não está logado redireciona para a página de login
    if g.usuario == '':
        return redirect(url_for('login'))

    # Página de destino de logout
    resposta = make_response(redirect(url_for('login')))

    # apaga o cookie do usuário
    resposta.set_cookie(
        key='usuario',  # Nome do cookie
        value='',  # Apara o valor do cookie
        max_age=0  # A validade do cookie é ZERO
    )

    # Redireciona para login
    return resposta


@app.route('/cadastro', methods=['GET', 'POST'])  # Cadastro de usuário
def cadastro():

    # Verifica se o usuário está logado → Pelo cookie
    if g.usuario != '':
        # Se o usuário está logado
        # Redireciona para a página inicial
        return redirect(url_for('index'))

    # Dados, variáveis e valores a serem passados para o template HTML
    pagina = {
        'titulo': 'Acessorios Afro - Cadastre-se',
    }

    return render_template('cadastro.html', **pagina)


@app.route('/novasenha', methods=['GET', 'POST'])  # Pedido de senha de usuário
def novasenha():

    novasenha = ''
    erro = False

    # Verifica se o usuário está logado → Pelo cookie
    if g.usuario != '':
        # Se o usuário está logado
        # Redireciona para a página inicial
        return redirect(url_for('index'))

    # Se o formulário foi enviado
    if request.method == 'POST':

        # Obtém dados preenchidos
        form = dict(request.form)

        # Teste de mesa
        # print('\n\n\nFORM:', form, '\n\n\n')

        # Pesquisa pelo email e nascimento informados, no banco de dados
        sql = '''
            SELECT u_id
            FROM usuario
            WHERE u_email = %s
                AND u_nascimento = %s
                AND u_status = 'on'
        '''
        cur = mysql.connection.cursor()
        cur.execute(sql, (form['email'], form['nascimento'],))
        row = cur.fetchone()
        cur.close()

        # Teste de mesa
        # print('\n\n\nDB:', row, '\n\n\n')

        # Se o usuário existe
        if row == None:

            erro = True

        else:
            # Gera uma nova senha
            novasenha = gerar_senha()

            # Salva a nova senha no banco de dados
            sql = '''
                UPDATE usuario
                SET u_senha = SHA1(%s)
                WHERE u_id = %s
            '''
            cur = mysql.connection.cursor()
            cur.execute(sql, (novasenha, row['u_id'],))
            mysql.connection.commit()
            cur.close()

    # Dados, variáveis e valores a serem passados para o template HTML
    pagina = {
        'titulo': 'Acessorios AFRO - Nova Senha',
        'erro': erro,
        'novasenha': novasenha,
    }

    return render_template('novasenha.html', **pagina)


@app.route('/perfil')
def perfil():

    # Se o usuário não está logado redireciona para a página de login
    if g.usuario == '':
        return redirect(url_for('login'))

    # Calcula idade do usuário
    g.usuario['idade'] = calcular_idade(g.usuario['nascimento'])

    # Obtém a quantidade de trecos ativos os usuário
    sql = '''
        SELECT count(t_id) AS total
        FROM treco
        WHERE t_usuario = %s
            AND t_status = 'on'
    '''
    cur = mysql.connection.cursor()
    cur.execute(sql, (g.usuario['id'],))
    row = cur.fetchone()
    cur.close()

    # Teste de mesa
    # print('\n\n\n', row, '\n\n\n')

    g.usuario['total'] = row['total']

    # Dados, variáveis e valores a serem passados para o template HTML
    pagina = {
        'titulo': 'Acessorios Afros - Novo Treco',
        'usuario': g.usuario,  # Dados do cookie do usuário
    }

    # Renderiza o template HTML, passaod valores para ele
    return render_template('perfil.html', **pagina)


@app.route('/apagausuario')
def apagausuario():
    # Apaga um usuário do sistema
    # Também apaga todos os seus "trecos"

    # Se o usuário não está logado redireciona para a página de login
    if g.usuario == '':
        return redirect(url_for('login'))

    # Configura o status do usuário para 'del' no banco de dados
    sql = "UPDATE usuario SET u_status = 'del' WHERE u_id = %s"
    cur = mysql.connection.cursor()
    cur.execute(sql, (g.usuario['id'],))
    mysql.connection.commit()
    cur.close()

    # Configura o status dos trecos do usuário para 'del' no banco de dados
    sql = "UPDATE treco SET t_status = 'del' WHERE t_usuario = %s"
    cur = mysql.connection.cursor()
    cur.execute(sql, (g.usuario['id'],))
    mysql.connection.commit()
    cur.close()

    # Página de destino de logout
    resposta = make_response(redirect(url_for('login')))

    # apaga o cookie do usuário
    resposta.set_cookie(
        key='usuario',  # Nome do cookie
        value='',  # Apara o valor do cookie
        max_age=0  # A validade do cookie é ZERO
    )

    # Redireciona para login
    return resposta


@app.route('/editaperfil', methods=['GET', 'POST'])
def editaperfil():

    # Se o usuário não está logado redireciona para a página de login
    if g.usuario == '':
        return redirect(url_for('login'))

    if request.method == 'POST':

        form = dict(request.form)

        # print('\n\n\n FORM:', form, '\n\n\n')

        sql = '''
            UPDATE usuario
            SET u_nome = %s,
                u_nascimento = %s,
                u_email = %s
            WHERE u_id = %s
                AND u_senha = SHA1(%s)
        '''
        cur = mysql.connection.cursor()
        cur.execute(sql, (
            form['nome'],
            form['nascimento'],
            form['email'],
            g.usuario['id'],
            form['senha1'],
        ))
        mysql.connection.commit()
        cur.close()

        # Se pediu para trocar a senha
        if form['senha2'] != '':

            sql = "UPDATE usuario SET u_senha = SHA1(%s) WHERE u_id = %s AND u_senha = SHA1(%s)"
            cur = mysql.connection.cursor()
            cur.execute(sql, (
                form['senha2'],
                g.usuario['id'],
                form['senha1'],
            ))
            mysql.connection.commit()
            cur.close()

        return redirect(url_for('logout'))

    # Recebe dados do usuário
    sql = '''
        SELECT * FROM usuario
        WHERE u_id = %s
            AND u_status = 'on'    
    '''
    cur = mysql.connection.cursor()
    cur.execute(sql, (g.usuario['id'],))
    row = cur.fetchone()
    cur.close()

    # print('\n\n\n USER:', row, '\n\n\n')

    pagina = {
        'titulo': 'CRUDTrecos - Erro 404',
        'usuario': g.usuario,
        'form': row
    }
    return render_template('editaperfil.html', **pagina)


@app.errorhandler(404)
def page_not_found(e):
    pagina = {
        'titulo': 'CRUDTrecos - Erro 404',
        'usuario': g.usuario,
    }
    return render_template('404.html', **pagina), 404


# Executa o servidor HTTP se estiver no modo de desenvolvimento
# Remova / comente essas linhas no modo de produção
if __name__ == '__main__':
    app.run(debug=True,port=8000)
