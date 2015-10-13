#!/usr/bin/env python

#Prep action:
#you need to get the api key for alchemiapi
#http://www.alchemyapi.com/products/alchemylanguage/sentiment-analysis
#Additionally, I have placed this script in the same directory where the
#python wrapper for this API is located. There is necessary for me to pass
#the api key to the script so it can process the command correctly.
#^^^There is a slicker way to do it, but I'm lazy, and want to give you more work

#You also need to have mysql 5.0 or higher I believe (I'm using v.5.5.44)
#Know a password and have a user with correct permissions to access the databases
#DON'T USE AN ADMIN LOGIN BECAUSE SECURITY REASONS (Even though I'm a hypocrite) 

#Rate limiting steps!
#can only make 200 requests an hour for stocktwits
#can only make 1000 requests a day for alchemyapi


import time # Used to pause between program calls
from datetime import datetime # Used to format the dates correctly

import requests # Used to access api tools from stocktwits
from alchemyapi import AlchemyAPI # Wrapper for sentimentality analysis api
import _mysql # Wrapper for SQL commands
import MySQLdb # Wrapper for SQL commands
import sys #ummm, I forgot if I needed this, and I'm too afraid to remove it at this point.
import pytz
from pytz import timezone
import smtplib
#WARNING: This is my first thing I've actually tried to code in python, and I've never
#		  used SQL before yesterday, so be forewarned about the unholy mess around you.

#alchemyAPI object
alchemyapi = AlchemyAPI()

#Hardcoded stocks
#The first item in every tuple is the stock symbol, and the second item
#is used to keep track which "tweet" wa recovered last.
all_stocktwits = [ ["INTC", 0], ["AMD", 0], ["IBM", 0], ["NVDA", 0], ["ATVI", 0], ["OGXI", 0], ["NVAX", 0], ["SD", 0], ["JD", 0], ["PG", 0], ["DIS", 0], ["QCOM", 0], ["CYBR", 0], ["NFLX", 0], ["ILMN", 0], ["LLY", 0] ]


#Connect to mysql locally, and set up cursor to send commands to sql
		#WARNING: NOT RECOMMENDED TO SET IT UP THE WAY I DID.
		#replace passwd="" with sql password for the user
print "Connecting to mySQL..."
stocktwit_db = MySQLdb.connect(host="localhost",user="debian-sys-maint",passwd="Kcfe2mRJXt5vHtHu")
cursor = stocktwit_db.cursor()
	
#should move this to Cron (bash)

#open up email account
smtpObj = smtplib.SMTP('smtp.gmail.com', 587)
smtpObj.ehlo()
smtpObj.starttls()
smtpObj.login('jamesdkent21@gmail.com', 'heartking23')
#for use later
	

time_sweep = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
x = 0 #initialize counter for each stock, probably not necessary.
for x in range(0,len(all_stocktwits)):
	
	#Create and use an sql database for a stock
	db_create = 'CREATE DATABASE IF NOT EXISTS %s' % all_stocktwits[x][0]
	cursor.execute(db_create)
	cursor.execute('USE %s' % all_stocktwits[x][0])

	#names for TABLES in DATABASE (i.e. TABLE: AMD_summary, DB: AMD)
	raw_data_table = "%s_raw" % all_stocktwits[x][0]
	summary_data_table = "{0}_summary".format(all_stocktwits[x][0])
	#print summary_data_table
	table_create = "CREATE TABLE IF NOT EXISTS {0} (Date DATE, Message_Volume SMALLINT, Positive_Sentiment_Percentage FLOAT(5,2), Positive_Sentiment_Score FLOAT(16,15), Negative_Sentiment_Percentage FLOAT(5,2), Negative_Sentiment_Score FLOAT(16,15), Neutral_Sentiment_Percentage FLOAT(5,2), Most_Recent_Message BIGINT)".format(summary_data_table)
	cursor.execute(table_create)

	raw_table_create = "CREATE TABLE IF NOT EXISTS {0} (Date DATETIME, Message_Volume SMALLINT, Positive_Sentiment_Percentage FLOAT(5,2), Positive_Sentiment_Score FLOAT(16,15), Negative_Sentiment_Percentage FLOAT(5,2), Negative_Sentiment_Score FLOAT(16,15), Neutral_Sentiment_Percentage FLOAT(5,2), Most_Recent_Message BIGINT, Volume BIGINT, Price FLOAT(5,2),Ask_Size INT, Bid_Size INT, Short_Ratio FLOAT(5,2))".format(raw_data_table)
	cursor.execute(raw_table_create)
	#Save to DB, I like to save my work
	cursor.execute('COMMIT')

	#see if there are previous messages
	cursor.execute('SELECT Most_Recent_Message FROM {0} LIMIT 1'.format(summary_data_table))
	messageID_catchall = cursor.fetchall()
	messageID = messageID_catchall
	print "messageID",messageID
	if messageID_catchall:
		if messageID_catchall[0][0] is not None:
			all_stocktwits[x][1] = int(messageID[0][0])
			#cursor.execute('SELECT Date FROM {0} LIMIT 1'.format(summary_data_table))
			#date_tuple = cursor.fetchall
			#cursor.execute('UPDATE {0} SET Most_Recent_Message = {1} WHERE Date="{2:%Y}-{2:%m}-{2:%d}"'.format(summary_data_table,all_stocktwits[x][1],message_date_abb_obj))

	#sentiment_culm = 0
	#Get the data from stocktwits for the relevant stock
	print "Getting tweets from Stocktwits"
	stocktwit_obj = requests.get('https://api.stocktwits.com/api/2/streams/symbol/ric/%s.json?since=%d' % (all_stocktwits[x][0], all_stocktwits[x][1]))

	#find the newest message in the pile (if there are any new messages)
	#get newest message id from the table

	if str(stocktwit_obj.json()['cursor']['since']) != "None":
		all_stocktwits[x][1] = stocktwit_obj.json()['cursor']['since']
	print all_stocktwits[x][1]

	#make the raw table for this sweep
	#get raw data from yahoo finance
	Volume = int(requests.get("http://finance.yahoo.com/d/quotes.csv?s={0}&f=v".format(all_stocktwits[x][0])).json())
	Price = float(requests.get("http://finance.yahoo.com/d/quotes.csv?s={0}&f=b".format(all_stocktwits[x][0])).json())
	Ask_Size = int(requests.get("http://finance.yahoo.com/d/quotes.csv?s={0}&f=a5".format(all_stocktwits[x][0])).json())
	Bid_Size = int(requests.get("http://finance.yahoo.com/d/quotes.csv?s={0}&f=b6".format(all_stocktwits[x][0])).json())
	Short_Ratio = float(requests.get("http://finance.yahoo.com/d/quotes.csv?s={0}&f=s7".format(all_stocktwits[x][0])).json())
	print time_sweep
	cursor.execute('INSERT INTO {0} (Date, Volume, Price, Ask_Size, Bid_Size, Short_Ratio) VALUES ("{1}","{2}","{3}","{4}","{5}","{6}")'.format(raw_data_table,time_sweep,Volume,Price,Ask_Size,Bid_Size,Short_Ratio))
	#cursor.execute('INSERT INTO {0} (Date) VALUES ("{1}")'.format(raw_data_table,time_sweep))
	
	current_hour = (int(datetime.today().strftime("%H")))
	if current_hour < 16 and current_hour >= 8:
		Daily_Ave_Volume = int(requests.get("http://finance.yahoo.com/d/quotes.csv?s={0}&f=a2".format(all_stocktwits[x][0])).json())
		Volume_multiplier = (current_hour-7)/8.0
		Ave_Current_Volume = Daily_Ave_Volume*Volume_multiplier
		Volume_Check = float(Volume/Ave_Current_Volume)
		if Volume_Check > 1.15:
			smtpObj.sendmail('jamesdkent21@gmail.com','jamesdkent21@gmail.com', 'Subject: High Volume for {0}'.format(all_stocktwits[x][0]))
		Open_Price = float(requests.get("http://finance.yahoo.com/d/quotes.csv?s={0}&f=o".format(all_stocktwits[x][0])).json())
		Prev_Close_Price = float(requests.get("http://finance.yahoo.com/d/quotes.csv?s={0}&f=p".format(all_stocktwits[x][0])).json())
		Overnight_Change = float(Open_Price/Prev_Close_Price)
		if Overnight_Change < 0.95:
			smtpObj.sendmail('jamesdkent21@gmail.com','jamesdkent21@gmail.com', 'Subject: Large Overnight Price Decrease for {0}'.format(all_stocktwits[x][0]))
		Day_Change = float(Price/Open_Price)
		print "Day Change: ",Day_Change
		if Day_Change < 0.90:
			smtpObj.sendmail('jamesdkent21@gmail.com','jamesdkent21@gmail.com', 'Subject: Large Day Price Decrease for {0}'.format(all_stocktwits[x][0]))

	#SELECT * FROM raw_data_table ORDER BY Date LIMIT 1
	#measures how many "new" tweets need to be analyzed
	tweet_volume = 0
	new_volume = int(len(stocktwit_obj.json()['messages']))
	tweet_volume += new_volume

	#initialize percentages and scores for raw
	raw_positive_sentiment_percentage = 0.0
	raw_positive_sentiment_score = 0.0
	raw_negative_sentiment_percentage = 0.0
	raw_negative_sentiment_score = 0.0
	raw_neutral_sentiment_percentage = 0.0

	for message_num in range(0, new_volume):
		message_counter = message_num+1
		#get the dates for raw and averaged data
		#only using the averaged data now
		message_date_full = stocktwit_obj.json()['messages'][message_num]['created_at'][0:19]
		long_date_format = "%Y-%m-%dT%H:%M:%S"
		long_date_obj = datetime.strptime(message_date_full, long_date_format)
		message_timezone = pytz.utc
		tlong_date_obj = long_date_obj.replace(tzinfo = message_timezone)
		nlong_date_obj = tlong_date_obj.astimezone(pytz.timezone('US/Eastern'))

		#change timezone from utc to eastern
		message_date_abb = nlong_date_obj.strftime("%Y-%m-%d")
		print message_date_abb
		message_date_abb_obj = datetime.strptime(message_date_abb, '%Y-%m-%d')
		#cursor.execute('UPDATE {0} SET Most_Recent_Message = {1} WHERE Date="{2:%Y}-{2:%m}-{2:%d}"'.format(summary_data_table,all_stocktwits[x][1],message_date_abb_obj))

		#Save to DB, I like to save my work
		cursor.execute('COMMIT')
		print "The date of message: ",message_date_abb_obj
		print "the most recent message",all_stocktwits[x][1]
		
		#isolate the actual text
		tweet = stocktwit_obj.json()['messages'][message_num]['body']

		#get the sentiment of the tweet
		print "Getting sentiment analysis from alchemyapi"
		sentiment_resp = alchemyapi.sentiment('text', tweet)
		#print "sentiment_resp: ",sentiment_resp
		#print "tweet: ", tweet

		#Need to find way to encode sentences with strange links and characters
		#to be read by the alchemy api
		if sentiment_resp['status'] == "OK":
			sentiment_type = sentiment_resp['docSentiment']['type']
		else:
			sentiment_type = "neutral"

		if sentiment_type == "neutral":
			sentiment_value = 0
		else:
			sentiment_value = float(sentiment_resp['docSentiment']['score'])

		#PREPARE YOURSELF FOR NEEDLESS IF STATEMENTS AND SHITTY INITIALIZATIONS
		#try:
		#	sentiment_culm
		#except:
		#	sentiment_culm = 0

		#sentiment_culm = sentiment_culm+sentiment_value

		#Attempt to organize data in sql table, good luck!
		#Also, I though I could do basic math and simplify, but I'm too scared too
		#so be ready for chunky unwieldly equations
		print "Putting Results in SQL database"
		#########################################
		# Step 1: The Date
		##########################################
		#Get the date: http://i0.kym-cdn.com/photos/images/newsfeed/000/209/945/D6PfW.jpg?1322673184
		cursor.execute('SELECT Date From {0} WHERE Date = "{1}"'.format(summary_data_table,message_date_abb_obj))
		date_exist = cursor.fetchall()
		#print "does the date exist?",date_exist
		#print "this is the sentiment_type: ",sentiment_type
		if not date_exist:
			cursor.execute('INSERT INTO {0} (Date,Most_Recent_Message) VALUES ("{1:%Y}-{1:%m}-{1:%d}")'.format(summary_data_table, message_date_abb_obj))
		cursor.execute('UPDATE {0} SET Most_Recent_Message = {1} WHERE Date = "{2}"'.format(summary_data_table, all_stocktwits[x][1], message_date_abb_obj))


		##########################################
		# Step 2: The Message Volume
		##########################################
		#get the current Message Volume
		cursor.execute('SELECT Message_Volume From {0} WHERE Date = "{1:%Y}-{1:%m}-{1:%d}"'.format(summary_data_table,message_date_abb_obj))
		message_volume_exist = cursor.fetchall()

		#print "current_message_Volume: ",message_volume_exist
		if  message_volume_exist[0][0] is None:
			#print "the list is empty"
			message_volume = 1
			cursor.execute('UPDATE {0} SET Message_Volume = {1} WHERE Date="{2:%Y}-{2:%m}-{2:%d}"'.format(summary_data_table,message_volume,message_date_abb_obj))
		else: 
			#print "the list is not empty"
			message_volume = (int(message_volume_exist[0][0])+1)
			cursor.execute('UPDATE {0} SET Message_Volume = {1} WHERE Date="{2:%Y}-{2:%m}-{2:%d}"'.format(summary_data_table,message_volume,message_date_abb_obj))
			#local message
		cursor.execute('UPDATE {0} SET Message_Volume = {1} WHERE Date="{2}"'.format(raw_data_table,new_volume,time_sweep))
		##########################################
		# Step 3: The Positive Sentiment Percentage
		##########################################
		#Get the Positive_Sentiment_Percentage
		#This is the percent of the total volume of tweets that had positive sentiment
		cursor.execute('SELECT Positive_Sentiment_Percentage From {0} WHERE Date = "{1:%Y}-{1:%m}-{1:%d}"'.format(summary_data_table,message_date_abb_obj))
		Positive_Sentiment_Percentage_exist = cursor.fetchall()
		#print "Does Positive_Sentiment_Percentage_exist?: ",Positive_Sentiment_Percentage_exist
		if Positive_Sentiment_Percentage_exist[0][0] is None:
			if sentiment_type == "positive":
				Positive_Sentiment_Percentage = 100
				raw_positive_sentiment_percentage = ((((float(raw_positive_sentiment_percentage)/100.0)*(int(message_counter)-1.0))+1.0)/(int(message_counter)))*100.0
			else:
				Positive_Sentiment_Percentage = 0
				raw_positive_sentiment_percentage = ((((float(raw_positive_sentiment_percentage)/100.0)*(int(message_counter)-1.0)))/(int(message_counter)))*100.0
			cursor.execute('UPDATE {0} SET Positive_Sentiment_Percentage = {1} WHERE Date="{2:%Y}-{2:%m}-{2:%d}"'.format(summary_data_table, Positive_Sentiment_Percentage,message_date_abb_obj))
		else:
			Positive_Sentiment_Percentage=Positive_Sentiment_Percentage_exist[0][0]
			if sentiment_type == "positive":
				#print "old positive percentage: ",Positive_Sentiment_Percentage
				Positive_Sentiment_Percentage = ((((float(Positive_Sentiment_Percentage)/100.0)*(int(message_volume)-1.0))+1.0)/(int(message_volume)))*100.0
				raw_positive_sentiment_percentage = ((((float(raw_positive_sentiment_percentage)/100.0)*(int(message_counter)-1.0))+1.0)/(int(message_counter)))*100.0
				#print "new positive percentage: ",Positive_Sentiment_Percentage
			else:
				#print "old positive percentage: ",Positive_Sentiment_Percentage
				Positive_Sentiment_Percentage = ((((float(Positive_Sentiment_Percentage)/100.0)*(int(message_volume)-1.0)))/(int(message_volume)))*100.0
				raw_positive_sentiment_percentage = ((((float(raw_positive_sentiment_percentage)/100.0)*(int(message_counter)-1.0)))/(int(message_counter)))*100.0
				#print "new positive percentage: ",Positive_Sentiment_Percentage
			cursor.execute('UPDATE {0} SET Positive_Sentiment_Percentage = {1} WHERE Date="{2:%Y}-{2:%m}-{2:%d}"'.format(summary_data_table,Positive_Sentiment_Percentage,message_date_abb_obj))
		cursor.execute('UPDATE {0} SET Positive_Sentiment_Percentage = {1} WHERE Date="{2}"'.format(raw_data_table,raw_positive_sentiment_percentage,time_sweep))



		#Local calculation for raw table

		##########################################
		# Step 4: The Positive Sentiment Score
		##########################################
		#Get the Poitive_Sentiment_Score
		#This is how "positive" the tweet was on a scale from 0 - 1.
		cursor.execute('SELECT Positive_Sentiment_Score From {0} WHERE Date = "{1:%Y}-{1:%m}-{1:%d}"'.format(summary_data_table,message_date_abb_obj))
		Positive_Sentiment_Score_exist = cursor.fetchall()
		#print "Does Positive_Sentiment_Score_exist: ",Positive_Sentiment_Score_exist
		if Positive_Sentiment_Score_exist[0][0] is None:
			if sentiment_type == "positive":
				Positive_Sentiment_Score = float(sentiment_value)
				cursor.execute('UPDATE {0} SET Positive_Sentiment_Score = {1} WHERE Date="{2:%Y}-{2:%m}-{2:%d}"'.format(summary_data_table, Positive_Sentiment_Score,message_date_abb_obj))
		else:
			Positive_Sentiment_Score=Positive_Sentiment_Score_exist[0][0]
			if sentiment_type == "positive":
				#print "old positive sentiment score: ",Positive_Sentiment_Score
				Positive_Sentiment_Score = ((((float(Positive_Sentiment_Percentage)/100.0)*(int(message_volume)-1.0)*Positive_Sentiment_Score_exist[0][0])+sentiment_value)/((float(Positive_Sentiment_Percentage)/100.0)*(int(message_volume))))
				#print "new positive sentiment score: ",Positive_Sentiment_Score
				cursor.execute('UPDATE {0} SET Positive_Sentiment_Score = {1} WHERE Date="{2:%Y}-{2:%m}-{2:%d}"'.format(summary_data_table,Positive_Sentiment_Score,message_date_abb_obj))

		#raw data input
		if sentiment_type == "positive":
			raw_positive_sentiment_score = ((((float(raw_positive_sentiment_percentage)/100.0)*(int(message_counter)-1.0)*raw_positive_sentiment_score)+sentiment_value)/((float(raw_positive_sentiment_percentage)/100.0)*(int(message_counter))))
		cursor.execute('UPDATE {0} SET Positive_Sentiment_Score = {1} WHERE Date="{2}"'.format(raw_data_table,raw_positive_sentiment_score,time_sweep))

		##########################################
		# Step 5: The Negative Sentiment Percentage
		##########################################
		#Get the Negaive_Sentiment_Percentage
		#This is the percent of the total volume of tweets that had negative sentiment
		cursor.execute('SELECT Negative_Sentiment_Percentage From {0} WHERE Date = "{1:%Y}-{1:%m}-{1:%d}"'.format(summary_data_table,message_date_abb_obj))
		Negative_Sentiment_Percentage_exist = cursor.fetchall()
		#print "Does Negative_Sentiment_Percentage_exist: ",Negative_Sentiment_Percentage_exist
		if Negative_Sentiment_Percentage_exist[0][0] is None:
			if sentiment_type == "negative":
				Negative_Sentiment_Percentage = 100.0
				raw_negative_sentiment_percentage = ((((float(raw_negative_sentiment_percentage)/100.0)*(int(message_counter)-1.0))+1.0)/(int(message_counter)))*100.0
			else:
				Negative_Sentiment_Percentage = 0
				raw_negative_sentiment_percentage = ((((float(raw_negative_sentiment_percentage)/100.0)*(int(message_counter)-1.0)))/(int(message_counter)))*100.0
			cursor.execute('UPDATE {0} SET Negative_Sentiment_Percentage = {1} WHERE Date="{2:%Y}-{2:%m}-{2:%d}"'.format(summary_data_table,Negative_Sentiment_Percentage,message_date_abb_obj))
		else:
			Negative_Sentiment_Percentage = Negative_Sentiment_Percentage_exist[0][0]
			if sentiment_type == "negative":
				#print 'old negative percentage: ',Negative_Sentiment_Percentage
				Negative_Sentiment_Percentage = ((((float(abs(Negative_Sentiment_Percentage)/100.0))*(int(message_volume)-1.0))+1.0)/(int(message_volume)))*100.0
				raw_negative_sentiment_percentage = ((((float(raw_negative_sentiment_percentage)/100.0)*(int(message_counter)-1.0))+1.0)/(int(message_counter)))*100.0
				#print 'new negative percentage: ',Negative_Sentiment_Percentage
			else:
				#print 'old negative percentage: ',Negative_Sentiment_Percentage
				Negative_Sentiment_Percentage = ((((float(abs(Negative_Sentiment_Percentage)/100.0))*(int(message_volume)-1.0)))/(int(message_volume)))*100.0
				raw_negative_sentiment_percentage = ((((float(raw_negative_sentiment_percentage)/100.0)*(int(message_counter)-1.0)))/(int(message_counter)))*100.0
				#print 'new negative percentage: ',Negative_Sentiment_Percentage
			cursor.execute('UPDATE {0} SET Negative_Sentiment_Percentage = {1} WHERE Date="{2:%Y}-{2:%m}-{2:%d}"'.format(summary_data_table,Negative_Sentiment_Percentage,message_date_abb_obj))
		cursor.execute('UPDATE {0} SET Negative_Sentiment_Percentage = {1} WHERE Date="{2}"'.format(raw_data_table,raw_negative_sentiment_percentage,time_sweep))

		##########################################
		# Step 6: The Negative Sentiment Score
		##########################################
		#Get the Negative_Sentiment_Score
		#This is how "positive" the tweet was on a scale from 0 - -1
		cursor.execute('SELECT Negative_Sentiment_Score From {0} WHERE Date = "{1:%Y}-{1:%m}-{1:%d}"'.format(summary_data_table,message_date_abb_obj))
		Negative_Sentiment_Score_exist = cursor.fetchall()
		#print "Does Negative_Sentiment_Score_exist: ",Negative_Sentiment_Score_exist
		if Negative_Sentiment_Score_exist[0][0] is None:
			if sentiment_type == "negative":
				Negative_Sentiment_Score = float(sentiment_value)
				cursor.execute('UPDATE {0} SET Negative_Sentiment_Score = {1} WHERE Date="{2:%Y}-{2:%m}-{2:%d}"'.format(summary_data_table,Negative_Sentiment_Score,message_date_abb_obj))
		else:
			Negative_Sentiment_Score = Negative_Sentiment_Score_exist[0][0] 
			if sentiment_type == "negative":
				#print 'old negative sentiment score: ',Negative_Sentiment_Score
				Negative_Sentiment_Score = ((((float(abs(Negative_Sentiment_Percentage)/100.0))*(int(message_volume)-1.0)*Negative_Sentiment_Score_exist[0][0])+sentiment_value)/((float(Negative_Sentiment_Percentage)/100.0)*(int(message_volume))))
				#print 'new negative sentiment score: ',Negative_Sentiment_Score
				cursor.execute('UPDATE {0} SET Negative_Sentiment_Score = {1} WHERE Date="{2:%Y}-{2:%m}-{2:%d}"'.format(summary_data_table,Negative_Sentiment_Score,message_date_abb_obj))

		#raw data input
		if sentiment_type == "negative":
			raw_negative_sentiment_score = ((((float(raw_negative_sentiment_percentage)/100.0)*(int(message_counter)-1.0)*raw_negative_sentiment_score)+sentiment_value)/((float(raw_negative_sentiment_percentage)/100.0)*(int(message_counter))))
		cursor.execute('UPDATE {0} SET Negative_Sentiment_Score = {1} WHERE Date="{2}"'.format(raw_data_table,raw_negative_sentiment_score,time_sweep))

		##########################################
		# Step 7: The Neutral Sentiment Percentage
		##########################################
		#Get the Neutral_Sentiment_Percentage
		#This is the percent of the total volume of tweets that had neutral sentiment
		#or I was unable to parse them.
		cursor.execute('SELECT Neutral_Sentiment_Percentage From {0} WHERE Date = "{1:%Y}-{1:%m}-{1:%d}"'.format(summary_data_table,message_date_abb_obj))
		Neutral_Sentiment_Percentage_exist = cursor.fetchall()
		#print "Does Neutral_Sentiment_Percentage_exist: ",Neutral_Sentiment_Percentage_exist
		if Neutral_Sentiment_Percentage_exist[0][0] is None:
			if sentiment_type == "neutral":
				Neutral_Sentiment_Percentage = 100
				raw_neutral_sentiment_percentage = ((((float(raw_neutral_sentiment_percentage)/100.0)*(int(message_counter)-1.0))+1.0)/(int(message_counter)))*100.0
			else:
				Neutral_Sentiment_Percentage = 0
				raw_neutral_sentiment_percentage = ((((float(raw_neutral_sentiment_percentage)/100.0)*(int(message_counter)-1.0)))/(int(message_counter)))*100.0
			cursor.execute('UPDATE {0} SET Neutral_Sentiment_Percentage = {1} WHERE Date="{2:%Y}-{2:%m}-{2:%d}"'.format(summary_data_table, Neutral_Sentiment_Percentage,message_date_abb_obj))
		else:
			Neutral_Sentiment_Percentage = Neutral_Sentiment_Percentage_exist[0][0]
			if sentiment_type == "neutral": 
				#print 'old neutral percentage',Neutral_Sentiment_Percentage
				Neutral_Sentiment_Percentage = ((((float(Neutral_Sentiment_Percentage)/100.0)*(int(message_volume)-1.0))+1.0)/(int(message_volume)))*100.0
				raw_neutral_sentiment_percentage = ((((float(raw_neutral_sentiment_percentage)/100.0)*(int(message_counter)-1.0))+1.0)/(int(message_counter)))*100.0
			else:
				#print 'old neutral percentage',Neutral_Sentiment_Percentage
				Neutral_Sentiment_Percentage = ((((float(Neutral_Sentiment_Percentage)/100.0)*(int(message_volume)-1.0)))/(int(message_volume)))*100.0
				raw_neutral_sentiment_percentage = ((((float(raw_neutral_sentiment_percentage)/100.0)*(int(message_counter)-1.0)))/(int(message_counter)))*100.0

			#print 'new neutral percentage',Neutral_Sentiment_Percentage
			cursor.execute('UPDATE {0} SET Neutral_Sentiment_Percentage = {1} WHERE Date="{2:%Y}-{2:%m}-{2:%d}"'.format(summary_data_table,Neutral_Sentiment_Percentage,message_date_abb_obj))
		cursor.execute('UPDATE {0} SET Neutral_Sentiment_Percentage = {1} WHERE Date="{2}"'.format(raw_data_table,raw_neutral_sentiment_percentage,time_sweep))

		cursor.execute('COMMIT')

		
	
	#if current_hour < 16 and current_hour >= 8
	
	#print "the stock: ",all_stocktwits[x][0]
	#print "the culmulative sentiment: ",sentiment_culm
	cursor.execute('COMMIT')
#time.sleep(3600) #wait 60 seconds, debugging speed?




#cursor.execute('INSERT INTO also_test_table VALUES (2015-10-05, 356, 33.45565, 0.643232, 33.09, 0.7232, 33.262)')



#get current value
#SELECT Positive_Sentiment_Percentage FROM blank_space_baby  WHERE Date = '2015-10-05';


#update step
#date_thing.strftime("%Y-%m-%d")


#cursor.execute('INSERT INTO also_test_table VALUES ("{0:%Y}-{0:%m}-{0:%d}", {1}, {2}, {3}, {4}, {5}, {6})'.format(date_thing,432,32.09,0.7632,34.59,0.563,33.33))
#cursor.execute('INSERT INTO also_test_table VALUES ("{0:%Y}-{0:%m}-{0:%d}", 356, 33.455, 0.643232, 33.09, 0.7232, 33.262)'.format(date_thing, "year", "month", "day"))
#SELECT Positive_Sentiment_Percentage FROM also_test_table WHERE Date = '2015-10-05';




#cursor.execute('SELECT Positive_Sentiment_Percentage FROM also_test_table  WHERE Date = "{0:%Y}-{0:%m}-{0:%d}"'.format(date_thing))
#sentiments = cursor.fetchall()

#if not sentiments:
	#SQL plain UPDATE summary_data_table SET Positive_Sentiment_Percentage = 10 WHERE Date = date_thing
#	cursor.execute('INSERT INTO blank_space_baby (Date) VALUES ("{0:%Y}-{0:%m}-{0:%d}")'.format(date2))
