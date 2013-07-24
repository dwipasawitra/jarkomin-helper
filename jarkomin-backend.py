#!/usr/bin/python
# JARKOM.IN Backend Sender System

import json, urllib, urllib2
import _mysql, MySQLdb, time
import datetime

server_addr = 'http://jarkom.in/demo'

def process_sender():
	# Read SMS from database
	con = MySQLdb.connect('localhost', 'root', '', 'gammu')
	cur = con.cursor(MySQLdb.cursors.DictCursor)
	cur.execute("SELECT * FROM inbox where Processed = 'false'")
	inbox_rows = cur.fetchall()
	for inbox in inbox_rows:
		# Read sender and its content
		sms_src = inbox['SenderNumber']
		sms_msg = inbox['TextDecoded']
			
		# Send it to JARKOM.IN Web Apps
		req_url = server_addr + '/index.php/api_jarkomin/proses_sms_masuk'
		req_params = urllib.urlencode(dict(no_handphone=sms_src, konten=sms_msg, api_id='jarkominmantebjaya', api_secret_code='semogalolosdikt'))
		request = urllib2.urlopen(req_url, req_params)
		response = request.read()		
	
		print "SMS RCVD: {0}: {1}".format(sms_src, sms_msg)
			
		# Delete it from database
		cur.execute("UPDATE inbox set Processed = 'true' WHERE ID=" + str(inbox['ID']))
			
	# Close MySQL Connection
	if con:
		con.close()
	return

# Define Indonesian Mobile Phone Operator Prefix Number
telkomsel_prefix = ["0811", "0812", "0813", "0821", "0822", "0823", "0852"]
xl_prefix = ["0817", "0818", "0819", "0859", "0874", "0876", "0877", "0878", "0879"]
indosat_prefix = ["0814", "0815", "0816", "0855", "0856", "0857", "0858"]
hutch_prefix = ["0899", "0898", "0897", "0896"]
axis_prefix = ["0838", "0832", "0831"]

# Another prefix, classified as CDMA/PSTN


def process_fetcher_sms():
	# Request Process
	req_url = server_addr + '/index.php/api_jarkomin/lihat_sms_siap_kirim'
	
	# We don't use it yet
	req_params = urllib.urlencode(dict(api_id='jarkominmantebjaya', api_secret_code='semogalolosdikt'))
	request = urllib2.urlopen(req_url, req_params)
	response = request.readline()

	# JSON Decode
	json_data = json.loads(response)

	# Connecting to MYSQL Server
	mysql_con = _mysql.connect('localhost', 'root', '', 'gammu')

	# Iterating data and entry to MYSQL Gammu server
	for i in json_data:
		sms_id = i['id_sms_pesanan']
		sms_dest = i['no_handphone']
		sms_msg = i['konten']
		sms_dest_prefix_num = sms_dest[:4]

		# Operator classification
		if(sms_dest_prefix_num in telkomsel_prefix):
			sms_op = "telkomsel"
		elif(sms_dest_prefix_num in xl_prefix):
			sms_op = "xl"
		elif(sms_dest_prefix_num in indosat_prefix):
			sms_op = "indosat"
		elif(sms_dest_prefix_num in hutch_prefix):
			sms_op = "hutch"
		elif(sms_dest_prefix_num in axis_prefix):
			sms_op = "axis"
		
		
		print "SMS SENT: " + sms_dest + ": " + sms_msg
		#mysql_con.query("INSERT INTO outbox(DestinationNumber, TextDecoded, SenderID) VALUES ('" + sms_dest + "','" + sms_msg + "','" + sms_op + ")")
		mysql_con.query("INSERT INTO outbox(DestinationNumber, TextDecoded) VALUES ('" + sms_dest + "','" + sms_msg + "')")

		# Mark the message as received
		req_url = server_addr + '/index.php/api_jarkomin/tandai_sms_sudah_terkirim'
		req_params = urllib.urlencode(dict(id_sms_pesanan=sms_id, api_id='jarkominmantebjaya', api_secret_code='semogalolosdikt'))
		request = urllib2.urlopen(req_url, req_params)
		response = request.readline()
		
	# Close MySQL Connection
	if mysql_con:
		mysql_con.close()
	return

def process_fetcher_fb():
	# Request Process
	req_url = server_addr + '/index.php/api_jarkomin/lihat_pesan_grup_siap_kirim'
	
	# We don't use it yet
	req_params = urllib.urlencode(dict(api_id='jarkominmantebjaya', api_secret_code='semogalolosdikt'))
	request = urllib2.urlopen(req_url, req_params)
	response = request.readline()

	# JSON Decode
	json_data = json.loads(response)

	# Iterating foreach data
	for i in json_data:
		msg_id = i['id_pesan']
		msg_dest = i['grup_fb']
		msg_msg = i['konten']
		
		
		print "FB MSG SENT: " + msg_dest + ": " + msg_msg
		
		# Run fb-sender.sh
		subprocess.call("./fb-sender.sh " + msg_dest + " '" + msg_msg + "'", shell=True); 

		# Mark the message as received
		req_url = server_addr + '/index.php/api_jarkomin/tandai_pesan_grup_sudah_terkirim'
		req_params = urllib.urlencode(dict(id_grup_pesan=msg_id, api_id='jarkominmantebjaya', api_secret_code='semogalolosdikt'))
		request = urllib2.urlopen(req_url, req_params)
		response = request.readline()
		
	
	return

while(1):
	process_fetcher_sms()
	process_fetcher_fb()
	process_sender()
	time.sleep(20)
