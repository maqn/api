from peewee import *
from playhouse.db_url import connect

import config

db = connect(config.db)

class BaseModel(Model):
	class Meta:
		database = db

class User(BaseModel):
	username = CharField()
	password = CharField()
	fullname = CharField()
	email = CharField()

class Sensor(BaseModel):
	MAC = CharField()
	name = CharField()
	longitude = DecimalField()
	latitude = DecimalField()
	is_indoor = BooleanField()
	owner = ForeignKeyField(User, related_name='sensors')


db.create_tables([User, Sensor], True)
