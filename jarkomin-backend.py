#!/usr/bin/python
# JARKOM.IN Backend Sender System

import json, urllib, urllib2
import _mysql, MySQLdb, time
import datetime, sys, getopt
import ConfigParser
import logging
import subprocess
import os

from math import ceil

def load_http(req_url, req_params):
	try:
		req_params = urllib.urlencode(req_params)
		request = urllib2.urlopen(req_url, req_params)
		response = request.read()
		return response
	except:
		logging.error("Error while connecting to JARKOM.IN Server. Exiting.")
		sys.exit(1)
	return ""
	
def prepare_log_file():
	logging.basicConfig(filename=logfile, format='%(asctime)s %(message)s', level=logging.DEBUG)
	return
	
def read_configuration(filename):
	global mysql_server, mysql_user, mysql_password, mysql_db, logfile, server_addr, fb_feature

	global telkomsel_phoneid, xl_phoneid, three_phoneid, axis_phoneid, indosat_phoneid
	config = ConfigParser.RawConfigParser()
	try:	
		config.read(filename)

		# Reading configuration file
		mysql_server = config.get("gammu-smsd", "server_mysql")
		mysql_user = config.get("gammu-smsd", "username_mysql")
		mysql_password = config.get("gammu-smsd", "password_mysql")
		mysql_db = config.get("gammu-smsd", "database_mysql")
		
		server_addr = config.get("jarkomin", "server")
		fb_feature = config.getboolean("jarkomin", "fb_feature")
		logfile = config.get("jarkomin", "logfile")

		telkomsel_phoneid = config.get("gammu-smsd-phoneid", "telkomsel_phoneid")
		xl_phoneid = config.get("gammu-smsd-phoneid", "xl_phoneid")
		indosat_phoneid = config.get("gammu-smsd-phoneid", "indosat_phoneid")
		three_phoneid = config.get("gammu-smsd-phoneid", "three_phoneid")
		axis_phoneid = config.get("gammu-smsd-phoneid", "axis_phoneid")
			
	except:
		logging.error("Error reading configuration file. Exiting.")
		sys.exit(1)
		
	return

def process_sender():
	# Read SMS from database
	try:
		con = MySQLdb.connect(mysql_server, mysql_user, mysql_password, mysql_db)	
		cur = con.cursor(MySQLdb.cursors.DictCursor)
		
		# First, process non multipart message
		cur.execute("SELECT * FROM inbox where Processed = 'false' AND UDH = ''")
		inbox_rows = cur.fetchall()
		for inbox in inbox_rows:
			# Read sender and its content
			sms_src = inbox['SenderNumber']
			sms_msg = inbox['TextDecoded']
			
			# Send it to JARKOM.IN Web Apps
			load_http(server_addr + '/index.php/api_jarkomin/proses_sms_masuk', dict(no_handphone=sms_src, konten=sms_msg))
	
			logging.info("SMS RCVD: {0}: {1}".format(sms_src, sms_msg))
			
			# Delete it from database
			cur.execute("UPDATE inbox set Processed = 'true' WHERE ID=" + str(inbox['ID']))
		
		# Second, process multiparted message
		cur.execute("SELECT GROUP_CONCAT(ID separator ',') AS id_concat, SenderNumber, GROUP_CONCAT(TextDecoded SEPARATOR '') AS TextDecoded FROM inbox WHERE Processed='false' GROUP BY LEFT(UDH, 10)")
		inbox_rows = cur.fetchall()
		for inbox in inbox_rows:
			# Read sender and its content
			sms_src = inbox['SenderNumber']
			sms_msg = inbox['TextDecoded']
			
			# Send it to JARKOM.IN Web Apps
			load_http(server_addr + '/index.php/api_jarkomin/proses_sms_masuk', dict(no_handphone=sms_src, konten=sms_msg))
	
			logging.info("SMS RCVD: {0}: {1}".format(sms_src, sms_msg))
			
			# Delete it from database
			id_concat = str(inbox['id_concat']).split(",")
			for id in id_concat:
				cur.execute("UPDATE inbox set Processed = 'true' WHERE ID=" + id)

		# Close MySQL Connection
		if con:
			con.close()
		return
	except MySQLdb.Error:
		logging.error("Error while connecting to MySQL database.")
		sys.exit(1)
# Define Indonesian Mobile Phone Operator Prefix Number
telkomsel_prefix = ["0811", "0812", "0813", "0821", "0822", "0823", "0852"]
xl_prefix = ["0817", "0818", "0819", "0859", "0874", "0876", "0877", "0878", "0879"]
indosat_prefix = ["0814", "0815", "0816", "0855", "0856", "0857", "0858"]
hutch_prefix = ["0899", "0898", "0897", "0896"]
axis_prefix = ["0838", "0832", "0831"]

# Another prefix, classified as CDMA/PSTN


def process_fetcher_sms():
	# Request Process
	response = load_http(server_addr + '/index.php/api_jarkomin/lihat_sms_siap_kirim', dict(api_id='jarkominmantebjaya', api_secret_code='semogalolosdikt'))

	# JSON Decode
	json_data = json.loads(response)

	# Connecting to MYSQL Server
	try:
		mysql_con = MySQLdb.connect(mysql_server, mysql_user, mysql_password, mysql_db)
		mysql_cur = mysql_con.cursor()

		multipart_counter = 0

		# Iterating data and entry to MYSQL Gammu server
		for i in json_data:
			sms_id = i['id_sms_pesanan']
			sms_dest = i['no_handphone']
			sms_msg = i['konten']
			sms_dest_prefix_num = sms_dest[:4]

			# Operator classification
			if(sms_dest_prefix_num in telkomsel_prefix):
				sms_op = telkomsel_phoneid
			elif(sms_dest_prefix_num in xl_prefix):
				sms_op = xl_phoneid
			elif(sms_dest_prefix_num in indosat_prefix):
				sms_op = indosat_phoneid
			elif(sms_dest_prefix_num in hutch_prefix):
				sms_op = three_phoneid
			elif(sms_dest_prefix_num in axis_prefix):
				sms_op = axis_phoneid
			else:
				sms_op = three_phoneid
		
			logging.info ("SMS SENT via " + sms_op + ": " + sms_dest + ": " + sms_msg)

			# Check SMS part number
			sms_part = int(len(sms_msg)/160)

			if sms_part == 1:
				mysql_cur.execute("INSERT INTO outbox(DestinationNumber, TextDecoded, SenderID) VALUES ('" + sms_dest + "','" + sms_msg + "','" + sms_op + "')")
			else:
				# Send multipart message
				UDH_prefix = "050003" + ("%2x" % multipart_counter).replace(" ", "0").upper() + ("%02d" % sms_part)
				multipart_counter = multipart_counter + 1
				
				# Split the message by size
				message_splited = [ sms_msg[i:i+160] for i in range(0, len(sms_msg), 160) ]
				
				mysql_cur.execute("INSERT INTO outbox(DestinationNumber, TextDecoded, SenderID, UDH, MultiPart) VALUES ('" + sms_dest + "','" + message_splited[0] + "','" + sms_op + "','" + UDH_prefix + "01" + "', 'true')")
				
				last_id = mysql_cur.lastrowid
				
				for UDH_count in range(2, sms_part+1):
					mysql_cur.execute("INSERT INTO outbox_multipart(ID, SequencePosition, TextDecoded, UDH) VALUES ('" + str(int(last_id)) + "','" + str(UDH_count) + "','" + message_splited[UDH_count-1] + "','" + UDH_prefix + ("%02d" % UDH_count) + "')")
				
			# Mark the message as received
			load_http(server_addr + '/index.php/api_jarkomin/tandai_sms_sudah_terkirim', dict(id_sms_pesanan=sms_id, api_id='jarkominmantebjaya', api_secret_code='semogalolosdikt'))
		
		# Close MySQL Connection
		if mysql_con:
			mysql_con.close()
		return
	except MySQLdb.Error:
		logging.error("Error while connecting to MySQL database.")
		sys.exit(1)

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
		
		
		logging.info("FB MSG SENT: " + msg_dest + ": " + msg_msg)
		
		# Run fb-sender.sh
		subprocess.call(["./fb-sender.sh", msg_dest, msg_msg]); 

		# Mark the message as received
		req_url = server_addr + '/index.php/api_jarkomin/tandai_pesan_grup_sudah_terkirim'
		req_params = urllib.urlencode(dict(id_grup_pesan=msg_id, api_id='jarkominmantebjaya', api_secret_code='semogalolosdikt'))
		request = urllib2.urlopen(req_url, req_params)
		response = request.readline()
		
	
	return


def do_backend(configfile):
	i = 0
	read_configuration(configfile)
	prepare_log_file()	
	while(1):
		logging.info("Starting JARKOM.IN Backend System...")
		logging.info("** Iteration #" + str(i))
		logging.info("Fetch SMS from app..")
		process_fetcher_sms()
		if (fb_feature):
			logging.info("Fetch FB Message from app..")
			process_fetcher_fb()
		logging.info("Send retrieved SMS to app..")
		process_sender()
		logging.info("Wait for 20 seconds for next iteration..")
		time.sleep(20)
		i = i + 1
	return

def main():
	# Look at the argument
	optlist, args = getopt.getopt(sys.argv[1:], "hc:")
	config = "./jarkomin-backend.ini"
	for opt, arg in optlist:
		if(opt == '-h'):
			print 'JARKOMIN Backend System'
			print 'Argument list:'
			print '-h -- Show this help'
			print '-c <config-file> -- Defined config file location'
			print 'By default, this script would look at \"jarkomin-backend.py\" file'
			sys.exit(0)
		elif(opt == '-c'):
			config = arg
		
	
	do_backend(config)
	return
	
main()
		
