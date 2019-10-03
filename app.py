from flask import Flask, render_template, request, redirect #,Response, make_response, send_file
import os
import pandas as pd
import io
#import numpy as np
#import models as algorithms
#import plotfunctions as plotfun
import matplotlib.pyplot as plt
#from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
#from matplotlib.figure import Figure
#from io import BytesIO

app = Flask(__name__)

#variables globales donde se identifican los path para guardar los archivos en el proyecto
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_ROOT_CSVS = os.path.join(APP_ROOT, 'datos_csv/')
APP_ROOT_CSVS_GRAFICAS = os.path.join(APP_ROOT_CSVS, 'graficas/')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/csv')
@app.route('/csv', methods = ['POST'])
def csv():   
    return render_template('csv.html', vista= 1)

@app.route('/upload', methods=['POST'])
def upload():
    #ruta = os.path.join(APP_ROOT, 'datos_csv/')
    #ruta = APP_ROOT + 'datos_csv/'
    try:
        file = request.files['file']
    except:
        file = None
    
    if file:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)

        if not os.path.isdir(APP_ROOT_CSVS):
            os.mkdir(APP_ROOT_CSVS)

        filename = file.filename
        destino = "/".join([APP_ROOT_CSVS, filename])

        #se carga el archivo csv a un objeto pandas
        df_csv = pd.read_csv(stream, sep=",")

        #se borran todos los registros con campos nulos
        df_csv = df_csv.dropna()

        #se guarda el archivo como csv en la carpeta destino
        df_csv.to_csv(destino)


    return render_template('csv.html', df = df_csv, vista = 2)

@app.route('/graficar', methods=['POST', 'GET'])
def graficar():
    #variables del formulario
    variables_grafica = request.form
    filename = request.form['filename']

    #se carga el archivo de la ruta especificada
    ruta_dataset  = "/".join([APP_ROOT_CSVS, filename])
    df = pd.read_csv(ruta_dataset, sep=',')

    ruta_grafica = crear_grafica(variables_grafica,df)
    
    return render_template('csv.html', grafica = ruta_grafica, vista = 3)

    #return render_template('csv.html', df = True)

def crear_grafica(variables, dataframe):
    eje_x = variables['eje_x']
    eje_y = variables['eje_y']
    titulo = variables['titulo_grafica']
    n_regis = int(variables['cantidad_registros'])
    label_x = variables['titulo_ejex']
    label_y = variables['titulo_ejey']

    plt.title(titulo)
    plt.xlabel(label_x)
    plt.ylabel(label_y)
    dataframe = dataframe.loc[:n_regis-1]
    #plt.axis([0, 100, -15, 15]) #[xmin, xmax, ymin, ymax]
    
    plt.plot(dataframe[eje_x], dataframe[eje_y])

    
    if not os.path.isdir(APP_ROOT_CSVS_GRAFICAS):
            os.mkdir(APP_ROOT_CSVS_GRAFICAS)
    ruta = "{}/magen1.png".format(APP_ROOT_CSVS_GRAFICAS)
    plt.savefig(ruta)

    return ruta
    



@app.route('/xlsx')
def xlsx():
    pass

@app.route('/mysql')
def mysql():
    pass


if __name__ == '__main__':
    app.run(debug=True, port=5000)