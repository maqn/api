from flask import Flask, request, jsonify
from flask_cache import Cache
from flask_cors import cross_origin
from influxdb import InfluxDBClient
from datetime import datetime

from db import Sensor
import config

app = Flask(__name__)
cache = Cache(app,config={'CACHE_TYPE': 'simple'})
app.secret_key = config.flask_secret_key

influx = InfluxDBClient(config.influx_host, 8086, config.influx_user, config.influx_pass, config.influx_db)

@app.route('/submit.php', methods=['POST'])
def incomingSensorData():
	data = request.get_json()

	datapoint = [{
		"measurement": "sensor_values_002",
		"tags": {
			"MAC": data['MAC'],
			"firmware": data['software_version']
		},
		"fields": {
			"pm10": float(data['sensors']['ppd42ns']['P1']['concentration']),
			"pm25": float(data['sensors']['ppd42ns']['P2']['concentration']),
			"pm10_avg": float(data['sensors']['ppd42ns']['P1']['concentration_avg']),
			"pm25_avg": float(data['sensors']['ppd42ns']['P2']['concentration_avg']),
			"temperature": float(data['sensors']['dht22']['temperature']),
			"humidity": float(data['sensors']['dht22']['humidity']),
			"uptime": int(data['uptime'])
		}
	}]
	influx.write_points(datapoint, time_precision = "s")
	return "success"

@app.route('/nodes.json')
@cache.cached(timeout=119)
@cross_origin()
def getNodeList():
	query = 'show tag values from "sensor_values_002" with key = "MAC";'
	rs = influx.query(query)

	nodes = map(lambda x: x['value'], rs.get_points())

	query = 'select * from sensor_values_002 GROUP BY MAC ORDER BY time DESC LIMIT 1'
	rs = influx.query(query)

	query = 'select * from sensor_values_002 GROUP BY MAC ORDER BY time ASC LIMIT 1'
	rs2 = influx.query(query)

	nodedata = {}

	for node in nodes:
		result = list(rs.get_points(tags = {"MAC": node}))[0]
		result2 = list(rs2.get_points(tags = {"MAC": node}))[0]

		try:
			dbdata = Sensor.get(Sensor.MAC == node)
		except:
			continue

		time_since_last_update = datetime.utcnow() - datetime.strptime(result['time'],"%Y-%m-%dT%H:%M:%SZ")
		online = (time_since_last_update.days * 86400 + time_since_last_update.seconds) < 60 * 5
		nodedata[node] = {
			"lastseen": result['time'],
			"firstseen": result2['time'],
			"flags": {
				"online": online,
				"indoor": dbdata.is_indoor
				},
			"statistics": {
				"pm10": result['pm10'],
				"pm25": result['pm25'],
				"pm10_avg": result['pm10_avg']/9,
				"pm25_avg": result['pm25_avg']/9,
				"temperature": result['temperature'],
				"humidity": result['humidity'],
				"uptime": result['uptime'] / 1000
				},
			"nodeinfo": {
				"node_id": node,
				"software": {
					"firmware": {
						"base": "PMsense-ESP",
						"release": result['firmware']
						}

					},
				"hostname": dbdata.name
				}
			}

		nodedata[node]["nodeinfo"]["owner"] = dbdata.owner.email
		nodedata[node]["nodeinfo"]["location"] = {
			"latitude": float(dbdata.latitude),
			"longitude": float(dbdata.longitude)
		}

	data = { "version":1, "nodes": nodedata, "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}

	return jsonify(data)