from flask import Flask, render_template, request, session, escape, send_from_directory, url_for
import os, io, datetime, random, matplotlib, sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from werkzeug.utils import secure_filename
matplotlib.rcParams.update({'font.size': 15}) 
  
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

#variables globales donde se identifican los path para guardar los archivos en el proyecto
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_DESCARGAS = os.path.join(APP_ROOT, 'static/descargas/')
APP_DESCARGAS_GRAFICAS = os.path.join(APP_DESCARGAS, 'graficas/')
APP_DESCARGAS_EXPORT = os.path.join(APP_DESCARGAS, 'exportaciones/')
APP_DESCARGAS_NUEVOS = os.path.join(APP_DESCARGAS, 'nuevos/')
ARCHIVOS_PERMITIDOS = ['csv', 'xlsx', 'db']
app.secret_key = '123456'

app.config['UPLOAD_FOLDER'] = APP_DESCARGAS

@app.route('/')
def index():
	return render_template('index.html')


@app.route('/csv/')
@app.route('/csv/', methods = ['POST'])
def csv():   
	if "data_user" in session:
		return action() 
	return render_template('csv.html', vista= 1)

def gestion_dataframe(extencion , filename , path, dataframe, stream, accion = "cargar",conn = "", date = False):
	if not os.path.isdir(path):
		os.mkdir(path)

	if date == True: 
		date = datetime.datetime.now()
		date = date.strftime("%d-%m-%Y %H%M%S")
		nombre_sin_ext = filename + date
	else:
		nombre_sin_ext = filename

	nombre_completo = nombre_sin_ext+ "." + extencion	
	ubicacion = "/".join([path, nombre_completo])
	if accion == 'cargar':
		if extencion == 'csv':
			df = pd.read_csv(ubicacion, sep=",")
		elif extencion == 'xlsx':
			#solo carga el contenido de la primer hoja del documento de excel
			df = pd.read_excel(ubicacion)
		elif extencion == 'db':
			con = sqlite3.connect(ubicacion)
			df = pd.read_sql_query("SELECT * FROM {};".format(escape(session["name_table"])), con)
			con.close()
		return df
	elif accion == 'guardar':
		try:
			os.remove(ubicacion)
		except:
			pass
		if extencion == "csv":
			dataframe.to_csv(ubicacion,  index=False)
		elif extencion == 'xlsx':
			dataframe.to_excel(ubicacion, sheet_name='hoja 1')
		elif extencion == 'db':
			con = sqlite3.connect(ubicacion)
			dataframe.to_sql(ubicacion, con=con, index=False, if_exists='replace')

@app.route('/csv/action')
@app.route('/csv/action', methods = ['GET','POST'])
def action():
	if "data_user" in session:
		return render_template("action_csv.html")
	else:
		if request.method == 'POST':
			try:
				file = request.files['file']

				if not os.path.isdir(APP_DESCARGAS):
					os.mkdir(APP_DESCARGAS)

				split_archivo = file.filename.split(".")
				if split_archivo[1] in ARCHIVOS_PERMITIDOS:
					filename = secure_filename(file.filename)
					path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
					file.save(path)
					session["name_file"] = filename.split('.')[0]
					session["extencion"] = split_archivo[1]
					session["data_user"] = filename
					if len(request.form['tabla_bd']) > 0 and split_archivo[1] == 'db':
						session["name_table"] = request.form['tabla_bd']
					else:
						session["name_table"] = ""
					
					return render_template('action_csv.html')
				else: 
					return csv()
				
			except:
				return csv()

	return csv()

@app.route('/csv/limpiar')
@app.route('/csv/limpiar', methods = ['POST'])
def limpiar_csv():
	df = gestion_dataframe(filename=escape(session["name_file"]), extencion=escape(session["extencion"]), path=APP_DESCARGAS, dataframe=[], stream="",accion= 'cargar')

	df_para_enviar = df
	vista = 1	
	hay_nulos = False
	try:
		action = int(request.args.get('action'))
	
		if (action > 0) and (action < 7):
			#(action = 1) opciones rapidas
			if action == 1:
				vista = 2 
				if df.isnull().values.any(): #se verifican que hallan campos NUll
					hay_nulos = True
					df_para_enviar = df[df.isnull().any(axis=1)]
					if request.args.get('eliminar'):
						df = df.dropna()
						gestion_dataframe(filename=escape(session["name_file"]), extencion=escape(session["extencion"]), path=APP_DESCARGAS,dataframe=df,stream="",accion= 'guardar')

						df_para_enviar = df 
						hay_nulos = False
				else: 
					hay_nulos = False	
			#(action = 2)seleccionar, eliminar o remplazar registros donde hallan campos vacios
			elif action == 2:
				vista = 3
				if df.isnull().values.any(): #se verifican que hallan campos NUll
					hay_nulos = True
					if request.method == 'POST':
						accion = request.form['accion']
						texto = request.form['new_texto']
						columna = request.form['columna']
						if accion == '1':
							df = df.replace({columna: {np.nan: texto}})
						elif accion == '2':
							df = df.replace({columna: {np.nan: 0}})
						elif accion == '3':
							df = df.dropna(subset=[columna])
						gestion_dataframe(filename=escape(session["name_file"]), extencion=escape(session["extencion"]), path=APP_DESCARGAS,dataframe=df,stream="",accion= 'guardar')
					null_columnas = df.columns[df.isnull().any()]
					df_para_enviar = df[null_columnas]
				else: 
					hay_nulos = False
			#(action = 3) seleccionar columnas para crear nuevo dataset
			elif action == 3:
				vista = 4
				#vista_nuevo = 1
				df_para_enviar = df.columns
				if request.method == 'POST':
					vista_nuevo = 2
					accion_nuevo = request.form['accion_nuevo']
					columnas = request.form
					nombre_columnas = []
					for columna in columnas:
						if columna != 'accion_nuevo':
							nombre_columnas.append(columna)
					nuevo_df = df[nombre_columnas]
					df_para_enviar = nuevo_df
					
					
					if accion_nuevo == 'editar':
						df = nuevo_df
						gestion_dataframe(filename=escape(session["name_file"]), extencion=escape(session["extencion"]), path=APP_DESCARGAS,dataframe=df,stream="",accion= 'guardar')
						df_para_enviar = df.columns
					elif accion_nuevo == 'descargar':
						if not os.path.isdir(APP_DESCARGAS_NUEVOS):
							os.mkdir(APP_DESCARGAS_NUEVOS)

						gestion_dataframe(filename=escape(session["name_file"]), extencion=escape(session["extencion"]), path=APP_DESCARGAS_NUEVOS,dataframe=nuevo_df,stream="",accion= 'guardar')

						return send_from_directory(APP_DESCARGAS_NUEVOS, escape(session["data_user"]), as_attachment=True)
			#(action = 4)eliminar columnas
			elif action == 4:
				vista = 5
				if request.method == 'POST':
					columna = request.form['columna_eliminar']
					df = df.drop([columna], axis=1)
					gestion_dataframe(filename=escape(session["name_file"]), extencion=escape(session["extencion"]), path=APP_DESCARGAS,dataframe=df,stream="",accion= 'guardar')
					df_para_enviar = df
			#(action = 5) renombrar columnas
			elif action == 5:
				vista = 6
				if request.method == 'POST':
					columnas = request.form
					df.rename(columns=columnas, inplace=True)
					gestion_dataframe(filename=escape(session["name_file"]), extencion=escape(session["extencion"]), path=APP_DESCARGAS,dataframe=df,stream="",accion= 'guardar')
	except:
		pass
	return render_template('limpiar_csv.html', dataframe = df_para_enviar, enumerate=enumerate, vista=vista, len = len, hay_NULL = hay_nulos)

@app.route('/csv/consultas')
@app.route('/csv/consultas', methods = ['POST'])
def consultas_csv():
	df = gestion_dataframe(filename=escape(session["name_file"]), extencion=escape(session["extencion"]), path=APP_DESCARGAS, dataframe=[], stream="",accion= 'cargar')

	df_para_enviar = df
	vista = 1
	hay_nulos = False
	df_filtrado = []
	df_ordenado = []
	
	try:
		action = int(request.args.get('action'))
	except:
		action = 0

	if (action > 0) and (action < 7):
		#(action = 1) ver columnas
		if action == 1:
			vista = 2 
			df_columna = df.iloc[:,0]
			try:
				columna = request.args.get('item')
				df_columna = df[columna]
			except:
				pass 
			return render_template('consultar_csv.html', dataframe = df_para_enviar, enumerate=enumerate, vista=vista, len = len,  dataframe_col = df_columna)

		#(action = 2)ver grupo de registros
		elif action == 2:
			vista = 3
			df_para_enviar = []
			hay_nulos = True
			if request.method == 'POST':
				cantidad = request.form['cantidad']
				if cantidad == "todos":
					df_para_enviar = df
				elif cantidad == "rango":
					inicio = int(request.form['inicio'])
					fin = int(request.form['fin'])
					if inicio <= fin:
						df_para_enviar = df.iloc[inicio:fin]
					else:
						df_para_enviar = df.iloc[fin:inicio]

		#(action = 3) filtrar por columnas
		elif action == 3:
			vista = 4
			#vista_nuevo = 1
			df_filtrado = []
			if request.method == 'POST':
				columnas = request.form.getlist('columnas')
				if len(columnas) > 0:
					df_filtrado = df.filter(items=columnas)
				else: 
					df_filtrado = []
						
		#(action = 4) filtrar por valor de columna
		elif action == 4:
			vista = 5
			df_filtrado = []
			if request.method == 'POST':
				try:
					columna = request.form['columna']
					tipo_columna = str(df[columna].dtypes)
					if tipo_columna == 'int64':
						valor = int(request.form['valor_filtro'])
					elif tipo_columna == 'float64':
						valor = float(request.form['valor_filtro'])
					elif tipo_columna == 'object':
						valor = str(request.form['valor_filtro'])

					df_filtrado = df[df[columna] == valor]	
				except:
					df_filtrado = []

		#(action = 5) renombrar columnas
		elif action == 5:
			vista = 6
			df_ordenado = []
			if request.method == 'POST':
				columna = request.form['columna']
				orden = request.form['orden']

				if orden == 'asd':
					direccion = False
				elif orden == 'des':
					direccion = True

				df_ordenado = df.sort_values(by=columna, ascending=direccion)
				
	return render_template('consultar_csv.html', dataframe = df_para_enviar, enumerate=enumerate, vista=vista, len = len, dataframe_filt = df_filtrado, dataframe_orde = df_ordenado)

@app.route('/csv/enviar_grafica')
def enviar_grafica():
	filename = escape(session["grafica"])
	return send_from_directory(APP_DESCARGAS_GRAFICAS,filename)

@app.route('/csv/graficas')
@app.route('/csv/graficas', methods = ['POST'])
def graficas():
	df = gestion_dataframe(filename=escape(session["name_file"]), extencion=escape(session["extencion"]), path=APP_DESCARGAS, dataframe=[], stream="",accion= 'cargar')
	df_para_enviar = df
	vista = 1
	file_name = [] 

	try:
		action = int(request.args.get('action'))
	except:
		action = 0

	if (action > 0) and (action < 7):
		#(action = 1) Grafica Lineal
		if action == 1:
			vista = 2 
			df_para_enviar = df
			if request.method == 'POST':
				ejex = request.form['ejeX']
				ejey = request.form['ejeY']
				cantidad_registros = request.form['cantidad_registros']
				titulo_grafica = request.form['titulo_grafica']
				labelx = request.form['titulo_ejex']
				labely = request.form['titulo_ejey']
				legend = request.form['legend']

				if len(cantidad_registros)==0:
					cantidad_registros = len(df)-1
				else:
					cantidad_registros = int(cantidad_registros)
 

				x = df[ejex][:cantidad_registros]
				y = df[ejey][:cantidad_registros]
				
				file_name = graficadora(x=x,y=y,tipo="lineal",title=titulo_grafica,etiqueta = legend, 
							labelx = labelx,labely=labely, path=APP_DESCARGAS_GRAFICAS)
				
		#(action = 2)Gráfica Columnas
		elif action == 2:
			vista = 3 
			df_para_enviar = df
			if request.method == 'POST':
				ejex = request.form['ejeX']
				ejey = request.form['ejeY']
				cantidad_registros = request.form['cantidad_registros']
				titulo_grafica = request.form['titulo_grafica']
				labelx = request.form['titulo_ejex']
				labely = request.form['titulo_ejey']
				legend = request.form['legend']


				if len(cantidad_registros)==0:
					cantidad_registros = len(df)-1
				else:
					cantidad_registros = int(cantidad_registros)
 

				x = df[ejex][:cantidad_registros]
				y = df[ejey][:cantidad_registros]

				file_name = graficadora(x=x,y=y,tipo="columnas",title=titulo_grafica,etiqueta = legend, 
							labelx = labelx,labely=labely, path=APP_DESCARGAS_GRAFICAS)

		#(action = 3) Gráfica barras
		elif action == 3:
			vista = 4 
			df_para_enviar = df
			if request.method == 'POST':
				ejex = request.form['ejeX']
				ejey = request.form['ejeY']
				cantidad_registros = request.form['cantidad_registros']
				titulo_grafica = request.form['titulo_grafica']
				labelx = request.form['titulo_ejex']
				labely = request.form['titulo_ejey']
				legend = request.form['legend']
			
				
				if len(cantidad_registros)==0:
					cantidad_registros = len(df)-1
				else:
					cantidad_registros = int(cantidad_registros)
 

				x = df[ejex][:cantidad_registros]
				y = df[ejey][:cantidad_registros]

				file_name = graficadora(x=y,y=x,tipo='barras',title=titulo_grafica,etiqueta = legend, 
							labelx = labelx,labely=labely, path=APP_DESCARGAS_GRAFICAS)
				
		#(action = 4) Gráfica Histograma
		elif action == 4:
			vista = 5 
			df_para_enviar = df
			if request.method == 'POST':
				ejex = request.form['ejeX']
				cantidad_registros = request.form['cantidad_registros']
				titulo_grafica = request.form['titulo_grafica']
				labelx = request.form['titulo_ejex']
				labely = request.form['titulo_ejey']
				legend = request.form['legend']
				
				
				if len(cantidad_registros)==0:
					cantidad_registros = len(df)-1
				else:
					cantidad_registros = int(cantidad_registros)
 

				x = df[ejex][:cantidad_registros]


				file_name = graficadora(x=x,tipo='histogr',title=titulo_grafica,etiqueta = legend, 
							labelx = labelx,labely=labely, path=APP_DESCARGAS_GRAFICAS)

		#(action = 5) Gráficar pie
		elif action == 5:
			vista = 6 
			df_para_enviar = df
			if request.method == 'POST':
				ejex = request.form['ejeX']
				ejey = request.form['ejeY']
				cantidad_registros = request.form['cantidad_registros']
				titulo_grafica = request.form['titulo_grafica']
				
				if len(cantidad_registros)==0:
					cantidad_registros = len(df)-1
				else:
					cantidad_registros = int(cantidad_registros)
 

				x = df[ejex][:cantidad_registros]
				y = df[ejey][:cantidad_registros]

				file_name = graficadora(x=x,y=y,tipo='porcentaje',title=titulo_grafica, path=APP_DESCARGAS_GRAFICAS)


	return render_template('graficas.html', dataframe = df_para_enviar, str=str,  vista=vista, len = len, enumerate=enumerate, path_grafica = file_name)

@app.route('/csv/action/exportar_dataset', methods = ['GET'])
def exportar_dataset():
	try:
		if "data_user" in session:
			tipo = int(request.args.get('tipo'))
			if 0 < tipo and tipo < 3:
				df = gestion_dataframe(filename=escape(session["name_file"]), extencion=escape(session["extencion"]), path=APP_DESCARGAS, dataframe=[], stream="",accion= 'cargar')

				if not os.path.isdir(APP_DESCARGAS_EXPORT):
						os.mkdir(APP_DESCARGAS_EXPORT)

				
				if tipo == 1:
					ubicacion = APP_DESCARGAS
					filename = escape(session['data_user']) 
				elif tipo == 2:
					filename = escape(session['name_file']) + ".xlsx"
					destino_archivo = "/".join([APP_DESCARGAS_EXPORT, filename])


					writer = pd.ExcelWriter(destino_archivo, engine='xlsxwriter')

					df.to_excel(writer, sheet_name='hoja 1')

					writer.save()
					

					ubicacion = APP_DESCARGAS_EXPORT

				return send_from_directory(ubicacion, filename, as_attachment=True)

			else:
				return "tipo %s" %tipo
		else:
			return "no session"
	except:
		return "hubo error para enviar archivo"

@app.route('/csv/especializada')
@app.route('/csv/especializada', methods = ['POST'])
def especializada():
	df = gestion_dataframe(filename=escape(session["name_file"]), extencion=escape(session["extencion"]), path=APP_DESCARGAS, dataframe=[], stream="",accion= 'cargar')

	dataframe = df
	result = False
	salida_comando = ""

	if request.method == 'POST':
		comando = str(request.form['comando'])

		if comando.find("df.") == -1 and comando.find("inplace")  == -1 and comando.find('os.') == -1:
			try:
				salida_comando = eval(comando)
			except:
				salida_comando = "Error en su sintaxis"
			finally:
				result = True	

	return render_template('especializada.html', result = result, salida_comando=salida_comando)

@app.route('/csv/action/cambiar_dataset')
def cambiar_dataset():
	try:
		archivo_eliminar = "/".join([APP_DESCARGAS, escape(session['data_user'])])
		os.remove(archivo_eliminar)
	except:
		pass
	try:
		destino_anterior = "/".join([APP_DESCARGAS_GRAFICAS, escape(session['grafica'])])
		os.remove(destino_anterior)
	except:
		pass
	try:
		destino_anterior = "/".join([APP_DESCARGAS_NUEVOS, escape(session['name_file'])])
		os.remove(destino_anterior)
		session.pop('name_file')
	except:
		pass
	try:
		archivo_eliminar = "/".join([APP_DESCARGAS_EXPORT, escape(session['data_user'])])
		os.remove(archivo_eliminar)
	except:
		pass
	session.pop('grafica', None)
	session.pop('data_user', None)
	return csv()

def guardar_grafica(ruta_carpeta, fig):
	if not os.path.isdir(ruta_carpeta):
		os.mkdir(ruta_carpeta)
	try:
		destino_anterior = "/".join([ruta_carpeta, escape(session['grafica'])])
		os.remove(destino_anterior)
	except:
		pass

	date = datetime.datetime.now()
	date = date.strftime("%d-%m-%Y_%H_%M_%S")

	session.pop('grafica', None)

	session['grafica'] = escape(session["name_file"])+ date + ".png"
	destino_archivo = "/".join([ruta_carpeta, escape(session['grafica'])])

	fig.savefig(destino_archivo)

	fig.clf()

	return escape(session['grafica'])

def deme_tamano_eje(cantidad_datos=int()):
    if cantidad_datos > 0 and cantidad_datos < 70:
        ejex = 5
        ejey = 5
    elif cantidad_datos >= 70 and cantidad_datos < 140:
        ejex = 8
        ejey = 8
    elif cantidad_datos >= 140 and cantidad_datos < 210:
        ejex = 14
        ejey = 14
    elif cantidad_datos >= 210:
        ejex = 17
        ejey = 17
        
    return (ejex, ejey)

def colores_aleatorios(num_colores=1):

    color = ["#"+''.join([random.choice('0123456789ABCDEF') for j in range(6)])
             for i in range(num_colores)]
    return color

def graficadora(x=[],y=[],tipo="lineal",title="Gráfica",etiqueta = "", labelx = "X",labely="Y", path=""): 
    tamano_fig = deme_tamano_eje(len(x))
    label = lambda x: True if len(etiqueta)>0 else False
    
    

    if tipo == "lineal":
        fig, ax = plt.subplots(figsize=tamano_fig)
        fig.tight_layout()
    
        ax.plot(x, y, label = etiqueta)

        ax.set(xlabel=labelx, ylabel=labely,
               title=title)
        
        if label(etiqueta):
            ax.legend()
        ax.grid()
        filename = guardar_grafica(path, fig)
        plt.close()
        return filename

    elif tipo == "columnas":
        #Ojo 'X' debe ser Int() o FLoat()
        fig, ax = plt.subplots(figsize=tamano_fig)
        fig.tight_layout()
        
        colores = colores_aleatorios(len(x.unique())+1)
        plt.bar(x, y, width = 0.8, color = colores)
        plt.xticks(x.unique(), tuple(x.unique().tolist()))
        ax.set(xlabel=labelx, ylabel=labely,
               title=title)
        if label(etiqueta):
           ax.legend()
        ax.grid()
        result = guardar_grafica(path, fig)
        plt.close()
        return result
    
    elif tipo == "barras":
        #"ojo colocar a 'X' en la ordenada como si fuera 'Y', 'X' debe ser Int() o Float()"
        fig, ax = plt.subplots(figsize=tamano_fig)
        colores = colores_aleatorios(len(y.unique())+1)
        plt.barh(y, x, color = colores)
        plt.xticks(x.unique(), tuple(x.unique().tolist()))
        ax.set(xlabel=labelx, ylabel=labely,
               title=title)
        if label(etiqueta):
            ax.legend()
            
        ax.grid()

        result = guardar_grafica(path, fig)
        plt.close()
        return result     

    elif tipo == "histogr":
        if str(x.dtypes) == 'int64' or str(x.dtypes) == 'float64':
            #solo se puede gráficar columnas int o float
            fig, ax = plt.subplots(figsize=tamano_fig)
            fig.tight_layout()


            data_ordenada = np.sort(x, axis=None) 
            plt.hist(data_ordenada, bins='auto', density=True, facecolor='g') 

            ax.set(xlabel=labelx, ylabel=labely,
                   title=title)

            if label(etiqueta):
                ax.legend()

            ax.grid()

            result = guardar_grafica(path, fig)

            return result
            plt.close()

        else:
            return "La serie de valores debe ser de tipo Int() o Float() "
    
    elif tipo == "porcentaje":
        f, (ax1, ax2) = plt.subplots(1, 2, sharex=True, figsize=(16,7))
        
        labels1 = x.value_counts().index.tolist()
        slices1 = x.value_counts().tolist()
        colores1 = colores_aleatorios(len(x.unique())+1)
        ax1.pie(slices1, labels = labels1, colors=colores1, startangle=90, radius = 1, autopct = '%1.1f%%') 
        ax1.set_title(x.name)
        ax1.grid()
        ax1.legend(bbox_to_anchor=(1.05, 1), loc=1, borderaxespad=0.)
        
        
        labels2 = y.value_counts().index.tolist()
        slices2 = y.value_counts().tolist()
        colores2 = colores_aleatorios(len(y.unique())+1)
        ax2.pie(slices2, labels = labels2, colors=colores2, startangle=90, radius = 1, autopct = '%1.1f%%') 
        ax2.set_title(y.name)
        ax2.grid()
        ax2.legend(bbox_to_anchor=(1.05, 1), loc=1, borderaxespad=0.)
        
        f.suptitle(title, va = 'bottom')

        result = guardar_grafica(path, f)
        plt.close()
        return result



if __name__ == '__main__':
	app.run(debug=True, port=5000)


	