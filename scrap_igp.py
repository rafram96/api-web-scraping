import requests
from bs4 import BeautifulSoup
import boto3
import uuid

def lambda_handler(event, context):
    # URL de la página con los sismos reportados
    url = "https://ultimosismo.igp.gob.pe/ultimo-sismo/sismos-reportados"

    # Solicitud HTTP a la página
    response = requests.get(url)
    if response.status_code != 200:
        return {'statusCode': response.status_code, 'body': 'Error al acceder a la página web'}

    # Parsear HTML
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table')
    if not table:
        return {'statusCode': 404, 'body': 'No se encontró la tabla de sismos en la página web'}

    # Extraer los primeros 10 sismos y mapear campos
    rows = []
    base_url = "https://ultimosismo.igp.gob.pe"
    for tr in table.find_all('tr')[1:11]:  # los 10 primeros registros
        cells = tr.find_all('td')
        entry = {}
        # URL al reporte sísmico
        link = cells[0].find('a')
        entry['reporte_url'] = f"{base_url}{link['href']}" if link and link.has_attr('href') else None
        # Detalles del sismo
        entry['referencia'] = cells[1].text.strip()
        entry['fecha_hora'] = cells[2].text.strip()
        entry['magnitud'] = cells[3].text.strip()
        # URLs de descargas
        a_tags = cells[4].find_all('a')
        entry['url_sismico'] = f"{base_url}{a_tags[0]['href']}" if len(a_tags) > 0 and a_tags[0].has_attr('href') else None
        if len(a_tags) > 1 and a_tags[1].has_attr('href'):
            entry['url_acelerometrico'] = a_tags[1]['href']
        rows.append(entry)

    # Almacenar en DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table_db = dynamodb.Table('TablaSismosIGP')

    # Eliminar registros anteriores
    scan = table_db.scan()
    with table_db.batch_writer() as batch:
        for item in scan.get('Items', []):
            batch.delete_item(Key={'id': item['id']})

    # Insertar nuevos registros con ID único
    for entry in rows:
        entry['id'] = str(uuid.uuid4())
        table_db.put_item(Item=entry)

    # Devolver resultado
    return {'statusCode': 200, 'body': rows}
