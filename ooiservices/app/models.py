#!/usr/bin/env python
'''
OOI Models
'''

__author__ = 'M@Campbell'

from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.sql import expression
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app
from flask.ext.sqlalchemy import BaseQuery
from ooiservices.app import db, login_manager
from flask.ext.login import UserMixin
from wtforms import ValidationError
from geoalchemy2.types import Geometry
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_searchable import make_searchable, SearchQueryMixin
from sqlalchemy_utils.types import TSVectorType
from datetime import datetime
import geoalchemy2.functions as func
import json

#--------------------------------------------------------------------------------

from collections import OrderedDict

class DictSerializableMixin(object):
    def serialize(self):
        return self._asdict()

    def _asdict(self):
        result = OrderedDict()
        for key in self.__mapper__.c.keys():
            result[key] = self._pytype(getattr(self, key))
        return result

    def _pytype(self, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v


#--------------------------------------------------------------------------------

class QueryMixin(BaseQuery, SearchQueryMixin):
    pass

#--------------------------------------------------------------------------------

__schema__ = 'ooiui'

class Annotation(db.Model, DictSerializableMixin):
    __tablename__ = 'annotations'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    reference_designator = db.Column(db.Text)
    user_id = db.Column(db.ForeignKey(u'' + __schema__ + '.users.id'), nullable=False)
    created_time = db.Column(db.DateTime(True), nullable=False, server_default=db.text("now()"))
    start_time = db.Column(db.DateTime(True), nullable=False)
    end_time = db.Column(db.DateTime(True), nullable=False)
    retired = db.Column(db.Boolean, server_default=expression.false())
    # Because we rely on uFrame, there won't be any sort of consistency checks.
    # We will be doing application level JOINs and if the stream_name doesn't
    # match a value from uFrame the record will be unaccounted for.
    stream_name = db.Column(db.Text())
    description = db.Column(db.Text())
    stream_parameter_name = db.Column(db.Text())

    user = db.relationship(u'User')

    @classmethod
    def from_dict(cls,data):
        rdict = {}
        rdict['reference_designator'] = data.get('reference_designator')
        rdict['user_id'] = data.get('user_id')
        rdict['start_time'] = data.get('start_time')
        rdict['end_time'] = data.get('end_time')
        rdict['stream_parameter_name'] = data.get('stream_parameter_name')
        rdict['description'] = data.get('description')

        # We would prefer the database generate this
        if 'created_time' in data:
            rdict['created_time'] = data.get('created_time')

        rdict['stream_name'] = data.get('stream_name')
        instance = cls(**rdict)
        return instance

class Array(db.Model):
    __tablename__ = 'arrays'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer(), primary_key=True)
    array_code = db.Column(db.Text())
    description = db.Column(db.Text())
    geo_location = db.Column(Geometry(geometry_type='GEOMETRY', srid=-1, dimension=2, spatial_index=True, management=True))
    array_name = db.Column(db.Text())
    display_name = db.Column(db.Text())

    def to_json(self):
        geo_location = None
        if self.geo_location is not None:
            geo_location = json.loads(db.session.scalar(func.ST_AsGeoJSON(self.geo_location)))
        json_array = {
            'id' : self.id,
            'array_code' : self.array_code,
            'description' : self.description,
            'geo_location' : geo_location,
            'array_name' : self.array_name,
            'display_name' : self.display_name
        }
        return json_array

    @staticmethod
    def from_json(json_post):
        array_code = json_post.get('array_code')
        description = json_post.get('description')
        geo_location = json_post.get('geo_location')
        array_name = json_post.get('array_name')
        display_name = json_post.get('display_name')
        return Array(array_code=array_code, description=description, \
        geo_location=geo_location, array_name=array_name, display_name=display_name)


class Assembly(db.Model):
    __tablename__ = 'assemblies'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    assembly_name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)

class AssetFileLink(db.Model):
    __tablename__ = 'asset_file_link'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.ForeignKey(u'' + __schema__ + '.assets.id'), nullable=False)
    file_id = db.Column(db.ForeignKey(u'' + __schema__ + '.files.id'), nullable=False)

    asset = db.relationship(u'Asset')
    file = db.relationship(u'File')

class AssetType(db.Model):
    __tablename__ = 'asset_types'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    asset_type_name = db.Column(db.Text, nullable=False)

class Asset(db.Model):
    __tablename__ = 'assets'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    asset_type_id = db.Column(db.ForeignKey(u'' + __schema__ + '.asset_types.id'), nullable=False)
    organization_id = db.Column(db.ForeignKey(u'' + __schema__ + '.organizations.id'), nullable=False)
    supplier_id = db.Column(db.Integer, nullable=False)
    deployment_id = db.Column(db.Integer)
    asset_name = db.Column(db.Text, nullable=False)
    model = db.Column(db.Text)
    current_lifecycle_state = db.Column(db.Text)
    part_number = db.Column(db.Text)
    firmware_version = db.Column(db.Text)
    geo_location = db.Column(Geometry(geometry_type='GEOMETRY', srid=-1, dimension=2, spatial_index=True, management=True))

    asset_type = db.relationship(u'AssetType')
    organization = db.relationship(u'Organization')

class DatasetKeyword(db.Model):
    __tablename__ = 'dataset_keywords'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.ForeignKey(u'' + __schema__ + '.datasets.id'), nullable=False)
    concept_name = db.Column(db.Text)
    concept_description = db.Column(db.Text)

    dataset = db.relationship(u'Dataset')

class Dataset(db.Model):
    __tablename__ = 'datasets'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    stream_id = db.Column(db.ForeignKey(u'' + __schema__ + '.streams.id'), nullable=False)
    deployment_id = db.Column(db.ForeignKey(u'' + __schema__ + '.deployments.id'), nullable=False)
    process_level = db.Column(db.Text)
    is_recovered = db.Column(db.Boolean, nullable=False, server_default=db.text("false"))

    deployment = db.relationship(u'Deployment')
    stream = db.relationship(u'Stream')

class Deployment(db.Model):
    __tablename__ = 'deployments'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    cruise_id = db.Column(db.Integer)

class DriverStreamLink(db.Model):
    __tablename__ = 'driver_stream_link'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.ForeignKey(u'' + __schema__ + '.drivers.id'), nullable=False)
    stream_id = db.Column(db.ForeignKey(u'' + __schema__ + '.streams.id'), nullable=False)

    driver = db.relationship(u'Driver')
    stream = db.relationship(u'Stream')

class Driver(db.Model):
    __tablename__ = 'drivers'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    instrument_id = db.Column(db.ForeignKey(u'' + __schema__ + '.instruments.id'))
    driver_name = db.Column(db.Text, nullable=False)
    driver_version = db.Column(db.Text)
    author = db.Column(db.Text)

    instrument = db.relationship(u'Instrument')

class File(db.Model):
    __tablename__ = 'files'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    file_name = db.Column(db.Text, nullable=False)
    file_system_path = db.Column(db.Text)
    file_size = db.Column(db.Text)
    file_permissions = db.Column(db.Text)
    file_type = db.Column(db.Text)

class InspectionStatus(db.Model):
    __tablename__ = 'inspection_status'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.ForeignKey(u'' + __schema__ + '.assets.id'), nullable=False)
    file_id = db.Column(db.ForeignKey(u'' + __schema__ + '.files.id'))
    status = db.Column(db.Text)
    technician_name = db.Column(db.Text)
    comments = db.Column(db.Text)
    inspection_date = db.Column(db.Date)
    document = db.Column(db.Text)

    asset = db.relationship(u'Asset')
    file = db.relationship(u'File')

class InstallationRecord(db.Model):
    __tablename__ = 'installation_records'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.ForeignKey(u'' + __schema__ + '.assets.id'), nullable=False)
    assembly_id = db.Column(db.ForeignKey(u'' + __schema__ + '.assemblies.id'), nullable=False)
    date_installed = db.Column(db.Date)
    date_removed = db.Column(db.Date)
    technician_name = db.Column(db.Text)
    comments = db.Column(db.Text)
    file_id = db.Column(db.ForeignKey(u'' + __schema__ + '.files.id'))

    assembly = db.relationship(u'Assembly')
    asset = db.relationship(u'Asset')
    file = db.relationship(u'File')

class InstrumentDeployment(db.Model):
    __tablename__ = 'instrument_deployments'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    platform_deployment_id = db.Column(db.ForeignKey(u'' + __schema__ + '.platform_deployments.id'))
    instrument_id = db.Column(db.ForeignKey(u'' + __schema__ + '.instruments.id'))
    reference_designator = db.Column(db.Text)
    depth = db.Column(db.Float)
    geo_location = db.Column(Geometry(geometry_type='GEOMETRY', srid=-1, dimension=2, spatial_index=True, management=True))

    instrument = db.relationship(u'Instrument')
    platform_deployment = db.relationship(u'PlatformDeployment')

    @staticmethod
    def from_json(json_post):
        display_name = json_post.get('display_name')
        start_date = json_post.get('start_date')
        end_date = json_post.get('end_date')
        platform_deployment_id = json_post.get('platform_deployment_id')
        #instrid = json_post.get('instrument_id')
        reference_designator = json_post.get('reference_designator')
        depth = json_post.get('depth')
        geo_location = json_post.get('geo_location')

        return InstrumentDeployment(
                display_name=display_name,
                start_date=start_date,
                end_date=end_date,
                platform_deployment_id=platform_deployment_id,
                depth=depth,
                reference_designator=reference_designator,
                geo_location=geo_location)

    def to_json(self):
        geo_location = None
        if self.geo_location is not None:
            json.loads(db.session.scalar(func.ST_AsGeoJSON(self.geo_location)))

        json_inst_deploy = {
            'id' : self.id,
            'reference_designator' : self.reference_designator,
            'platform_deployment_id' : self.platform_deployment_id,
            'display_name' : self.display_name,
            'depth' : self.depth,
            'start_date' : None,
            'end_date' : None,
            'geo_location' : geo_location
        }
        if self.start_date is not None:
            json_inst_deploy['start_date'] = self._pytype(self.start_date)
        if self.end_date is not None:
            json_inst_deploy['end_date'] = self._pytype(self.end_date)
        return json_inst_deploy

    def _pytype(self,v):
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)


class InstrumentModel(db.Model):
    __tablename__ = 'instrument_models'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    instrument_model_name = db.Column(db.Text, nullable=False)
    series_name = db.Column(db.Text)
    class_name = db.Column(db.Text)
    manufacturer_id = db.Column(db.ForeignKey(u'' + __schema__ + '.manufacturers.id'))

    manufacturer = db.relationship(u'Manufacturer')

class Instrumentname(db.Model):
    __tablename__ = 'instrumentnames'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    instrument_class = db.Column(db.Text)
    display_name = db.Column(db.Text)

class Instrument(db.Model):
    __tablename__ = 'instruments'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    instrument_name = db.Column(db.Text)
    description = db.Column(db.Text)
    location_description = db.Column(db.Text)
    instrument_series = db.Column(db.Text)
    serial_number = db.Column(db.Text)
    display_name = db.Column(db.Text)
    model_id = db.Column(db.ForeignKey(u'' + __schema__ + '.instrument_models.id'), nullable=False)
    asset_id = db.Column(db.ForeignKey(u'' + __schema__ + '.assets.id'), nullable=False)
    depth_rating = db.Column(db.Float)
    manufacturer_id = db.Column(db.ForeignKey(u'' + __schema__ + '.manufacturers.id'))

    asset = db.relationship(u'Asset')
    manufacturer = db.relationship(u'Manufacturer')
    model = db.relationship(u'InstrumentModel')

class LogEntry(db.Model):
    query_class = QueryMixin
    __tablename__ = 'log_entries'
    __table_args__ = {u'schema':__schema__}

    id = db.Column(db.Integer, primary_key=True)
    log_entry_type = db.Column(db.Text, nullable=False)
    entry_time = db.Column(db.DateTime(True), nullable=False, server_default=db.text("now()"))
    entry_title = db.Column(db.Text, nullable=False)
    entry_description = db.Column(db.Text)
    retired = db.Column(db.Boolean, server_default=expression.false())
    search_vector = db.Column(TSVectorType('entry_title', 'entry_description'))
    user_id = db.Column(db.ForeignKey(u'' + __schema__ + '.users.id'), nullable=False)
    organization_id = db.Column(db.ForeignKey(u'' + __schema__ + '.organizations.id'), nullable=False)

    user = db.relationship(u'User')
    organization = db.relationship(u'Organization')

    def to_json(self):
        return {
            'id' : self.id,
            'log_entry_type' : self.log_entry_type,
            'entry_time' : self.entry_time.isoformat(),
            'entry_title' : self.entry_title,
            'entry_description' : self.entry_description,
            'user' : {
                'id' : self.user_id,
                'first_name' : self.user.first_name,
                'last_name' : self.user.last_name
            },
            'organization' : {
                'id' : self.organization_id,
                'name' : self.organization.organization_name,
                'long_name' : self.organization.organization_long_name
            }
        }

    @classmethod
    def from_dict(cls, data):
        entry = cls()
        entry.log_entry_type = data.get('log_entry_type', 'INFO')
        if 'entry_title' not in data:
            raise ValueError('entry_title required to create LogEntry')
        entry.entry_title = data.get('entry_title')
        if 'entry_time' in data:
            entry.entry_time = data.get('entry_time')
        entry.entry_description = data.get('entry_description')
        entry.user_id = data.get('user_id')
        entry.organization_id = data.get('organization_id')
        return entry

class LogEntryComment(db.Model):
    __tablename__ = 'log_entry_comments'
    __table_args__ = {u'schema':__schema__}

    id = db.Column(db.Integer, primary_key=True)
    comment_time = db.Column(db.DateTime(True), nullable=False, server_default=db.text("now()"))
    comment = db.Column(db.Text)
    retired = db.Column(db.Boolean, server_default=expression.false())
    user_id = db.Column(db.ForeignKey(u'' + __schema__ + '.users.id'), nullable=False)
    log_entry_id = db.Column(db.ForeignKey(u'' + __schema__ + '.log_entries.id'), nullable=False)

    user = db.relationship(u'User')
    log_entry = db.relationship(u'LogEntry')

    def to_json(self):
        return {
            'id': self.id,
            'comment_time' : self.comment_time.isoformat(),
            'comment' : self.comment,
            'user' : {
                'id' : self.user.id,
                'name' : ' '.join([self.user.first_name, self.user.last_name])
            },
            'log_entry_id' : self.log_entry_id
        }

    @classmethod
    def from_dict(cls, data):
        comment = cls()
        if 'comment_time' in data:
            comment.comment_time = data.get('comment_time')
        comment.comment = data.get('comment')
        comment.user_id = data.get('user_id')
        comment.log_entry_id = data.get('log_entry_id')
        return comment

class Manufacturer(db.Model):
    __tablename__ = 'manufacturers'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    manufacturer_name = db.Column(db.Text, nullable=False)
    phone_number = db.Column(db.Text)
    contact_name = db.Column(db.Text)
    web_address = db.Column(db.Text)

class OperatorEventType(db.Model, DictSerializableMixin):
    __tablename__ = 'operator_event_types'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.Text, nullable=False)
    type_description = db.Column(db.Text)

    def to_json(self):
        json_operator_event_type_link = {
            'id' : self.id,
            'type_name' : self.type_name,
            'type_description' : self.type_description
        }
        return json_operator_event_type_link

    @staticmethod
    def insert_operator_event_types():
       event_info = OperatorEventType(type_name='INFO')
       event_info.type_description = 'General information event.'
       event_warn = OperatorEventType(type_name='WARN')
       event_warn.type_description = 'A warning has occurred.'
       event_error = OperatorEventType(type_name='ERROR')
       event_error.type_description = 'An error has occurred.'
       event_critical = OperatorEventType(type_name='CRITICAL')
       event_critical.type_description = 'A critical event has occurred.'
       event_start_watch = OperatorEventType(type_name='WATCH_START')
       event_start_watch.type_description = 'Watch has started.'
       event_end_watch = OperatorEventType(type_name='WATCH_END')
       event_end_watch.type_description = 'Watch has ended.'

       db.session.add_all([event_info, event_warn, event_error, event_critical, event_start_watch, event_end_watch])
       db.session.commit()


class OperatorEvent(db.Model, DictSerializableMixin):
    __tablename__ = 'operator_events'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    watch_id = db.Column(db.ForeignKey(u'' + __schema__ + '.watches.id'), nullable=False)
    operator_event_type_id = db.Column(db.ForeignKey(u'' + __schema__ + '.operator_event_types.id'), nullable=False)
    event_time = db.Column(db.DateTime(True), nullable=False, server_default=db.text("now()"))
    event_title = db.Column(db.Text, nullable=False)
    event_comment = db.Column(db.Text)

    operator_event_type = db.relationship(u'OperatorEventType')

    @staticmethod
    def from_json(json):
        watch_id = json.get('watch_id')
        operator_event_type_id = json.get('operator_event_type_id')
        event_time = json.get('event_time')
        event_title = json.get('event_title')
        event_comment = json.get('event_comment')

        #Return the OperatorEvent object ready to be stored.
        return OperatorEvent(watch_id=watch_id,
                             operator_event_type_id=operator_event_type_id,
                             event_time=event_time,
                             event_title=event_title,
                             event_comment=event_comment)


class Organization(db.Model, DictSerializableMixin):
    __tablename__ = 'organizations'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    organization_name = db.Column(db.Text, nullable=False)
    organization_long_name = db.Column(db.Text)
    image_url = db.Column(db.Text)

    users = db.relationship(u'User')

    @staticmethod
    def insert_org():
        org = Organization.query.filter(Organization.organization_name == 'RPS ASA').first()
        if org is None:
            org = Organization(organization_name = 'RPS ASA')
            db.session.add(org)
            db.session.commit()


class PlatformDeployment(db.Model, DictSerializableMixin):
    __tablename__ = 'platform_deployments'
    __table_args__ = {u'schema': __schema__}
    __searchable__ = ['display_name']

    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    platform_id = db.Column(db.ForeignKey(u'' + __schema__ + '.platforms.id'))
    reference_designator = db.Column(db.Text, nullable=False)
    array_id = db.Column(db.ForeignKey(u'' + __schema__ + '.arrays.id'))
    deployment_id = db.Column(db.ForeignKey(u'' + __schema__ + '.deployments.id'))
    display_name = db.Column(db.Text)
    geo_location = db.Column(Geometry(geometry_type='GEOMETRY', srid=-1, dimension=2, spatial_index=True, management=True))

    array = db.relationship(u'Array')
    deployment = db.relationship(u'Deployment')
    platform = db.relationship(u'Platform')

    @hybrid_property
    def geojson(self):
        return json.loads(db.session.scalar(func.ST_AsGeoJSON(self.geo_location)))

    @hybrid_property
    def proper_display_name(self):
        return self._get_display_name(reference_designator=self.reference_designator)

    def to_json(self):
        geo_location = None
        if self.geo_location is not None:
            loc = db.session.scalar(func.ST_AsGeoJSON(self.geo_location))
            geo_location = json.loads(loc)
        json_platform_deployment = {
            'id' : self.id,
            'reference_designator' : self.reference_designator,
            'array_id' : self.array_id,
            'display_name' : self.proper_display_name,
            'start_date' : self.start_date,
            'end_date' : self.end_date,
            'geo_location' : geo_location
        }
        return json_platform_deployment

    @classmethod
    def _f_concat_rd(cls, array_type, array_name, site, platform, assembly, instrument_name):

        if assembly is not None and instrument_name is not None:
            return array_type + ' ' + array_name + ' ' + site + ' ' + platform + ' - ' + assembly + ' - ' + instrument_name
        elif assembly is not None and instrument_name is None:
            return array_type + ' ' + array_name + ' ' + site + ' ' + platform + ' - ' + assembly
        else:
            return array_type + ' ' + array_name + ' ' + site + ' ' + platform

    @classmethod
    def _get_display_name(cls, reference_designator):

        '''
        sample reference_designators for tests:
            'CP02PMUO-SBS01-01-MOPAK0000'
            'GP05MOAS-GL002-03-ACOMMM000'
            'CE05MOAS-GL005'
            'CP05MOAS-AV001'
            'CP02PMUO-SBS01'

        curl -X GET http://localhost:4000/display_name?reference_designator=CP05MOAS-AV001
        '''

        import re
        if not reference_designator:
            return None

        rd_len = len(reference_designator)

        p_n = Platformname.query.filter(Platformname.reference_designator == reference_designator[:14]).first()
        if not p_n:
            return reference_designator

        if rd_len == 8:
            return cls._f_concat_rd(p_n.array_type, p_n.array_name, p_n.site, p_n.platform, None, None)

        elif rd_len == 14:
            assy = reference_designator[9:14]
            if re.match('AV[0-9]{3}', assy):
                platform_text = 'AUV ' + assy[2:5]
            elif re.match('GL[0-9]{3}', assy):
                platform_text = 'Glider ' + assy[2:5]
            else:
                platform_text = p_n.assembly

            return cls._f_concat_rd(p_n.array_type, p_n.array_name, p_n.site, p_n.platform, platform_text, None)

        elif rd_len == 27:
            inst = reference_designator[18:23]
            assy = reference_designator[9:14]
            if re.match('AV[0-9]{3}', assy):
                platform_text = 'AUV ' + assy[2:5]
            elif re.match('GL[0-9]{3}', assy):
                platform_text = 'Glider ' + assy[2:5]
            else:
                platform_text = p_n.assembly

            i_n = Instrumentname.query.filter(Instrumentname.instrument_class == inst).first()
            if not i_n:
                return cls._f_concat_rd(p_n.array_type, p_n.array_name, p_n.site, p_n.platform, platform_text, inst)

            return cls._f_concat_rd(p_n.array_type, p_n.array_name, p_n.site, p_n.platform, platform_text, i_n.display_name)
        return None

    def __repr__(self):
        return '{0}(display_name={1})'.format(self.__class__.__name__, self.display_name)


class Platformname(db.Model):
    __tablename__ = 'platformnames'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    reference_designator = db.Column(db.Text)
    array_type = db.Column(db.Text)
    array_name = db.Column(db.Text)
    site = db.Column(db.Text)
    platform = db.Column(db.Text)
    assembly = db.Column(db.Text)

class Platform(db.Model):
    __tablename__ = 'platforms'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    platform_name = db.Column(db.Text)
    description = db.Column(db.Text)
    location_description = db.Column(db.Text)
    platform_series = db.Column(db.Text)
    is_mobile = db.Column(db.Boolean, nullable=False)
    serial_no = db.Column(db.Text)
    asset_id = db.Column(db.ForeignKey(u'' + __schema__ + '.assets.id'), nullable=False)
    manufacturer_id = db.Column(db.ForeignKey(u'' + __schema__ + '.manufacturers.id'))

    asset = db.relationship(u'Asset')
    manufacturer = db.relationship(u'Manufacturer')

class StreamParameterLink(db.Model):
    __tablename__ = 'stream_parameter_link'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    stream_id = db.Column(db.ForeignKey(u'' + __schema__ + '.streams.id'), nullable=False)
    parameter_id = db.Column(db.ForeignKey(u'' + __schema__ + '.stream_parameters.id'), nullable=False)

    parameter = db.relationship(u'StreamParameter')
    stream = db.relationship(u'Stream')

class StreamParameter(db.Model):
    __tablename__ = 'stream_parameters'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    stream_parameter_name = db.Column(db.Text)
    short_name = db.Column(db.Text)
    long_name = db.Column(db.Text)
    standard_name = db.Column(db.Text)
    units = db.Column(db.Text)
    data_type = db.Column(db.Text)

    def to_json(self):
        json_parameter = {
            'id' : self.id,
            'parameter_name' : self.stream_parameter_name,
            'short_name' : self.short_name,
            'long_name' : self.long_name,
            'standard_name' : self.standard_name,
            'units' : self.units,
            'data_type' : self.data_type
        }
        return json_parameter


class Stream(db.Model):
    __tablename__ = 'streams'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    stream_name = db.Column(db.Text)
    instrument_id = db.Column(db.ForeignKey(u'' + __schema__ + '.instruments.id'))
    description = db.Column(db.Text)

    instrument = db.relationship(u'Instrument')

    def to_json(self):
        json_stream = {
            'id' : self.id,
            'stream_name' : self.stream_name,
            'instrument_id' : self.instrument_id,
            'description' : self.description
        }
        return json_stream


class SystemEventDefinition(db.Model):
    """
    Stores the definition for a single Alert/Alarm.
    Valid uframe operator values: 'GREATER', 'LESS', 'BETWEEN_EXCLUSIVE', 'OUTSIDE_EXCLUSIVE'
    """
    __tablename__ = 'system_event_definitions'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    uframe_filter_id = db.Column(db.Integer, nullable=False)
    reference_designator = db.Column(db.Text, nullable=False)
    array_name = db.Column(db.Text, nullable=False)
    platform_name = db.Column(db.Text, nullable=False)
    instrument_name = db.Column(db.Text, nullable=False)
    instrument_parameter = db.Column(db.Text, nullable=False)
    instrument_parameter_pdid = db.Column(db.Text, nullable=False)
    operator = db.Column(db.Text, nullable=False)
    created_time = db.Column(db.DateTime(True), nullable=False)
    event_type = db.Column(db.Text, nullable=False)
    active = db.Column(db.Boolean, nullable=False, server_default=db.text("false"))
    description = db.Column(db.Text, nullable=True)
    high_value = db.Column(db.Text, nullable=True)
    low_value = db.Column(db.Text, nullable=True)
    severity = db.Column(db.Integer, nullable=False)
    stream = db.Column(db.Text, nullable=False)
    retired = db.Column(db.Boolean, nullable=False, server_default=db.text("false")) # server_default=expression.false()
    ts_retired = db.Column(db.DateTime(True), nullable=True) # todo - should this be DateTime(False)?
    escalate_on = db.Column(db.Float, nullable=False)		 # amount of time, after the first alert occurred, to create a redmine ticket; seconds? units?)
    escalate_boundary = db.Column(db.Float, nullable=False)  # amount of time after ts_escalated to create yet another red mine ticket)

    '''
    @staticmethod
    def insert_system_event_definition(uframe_filter_id, reference_designator, array_name, platform_name,
                                       instrument_name, instrument_parameter, instrument_parameter_pdid, operator,
                                       created_time, event_type, active, description,
                                       high_value, low_value, severity, stream): #, escalate_on, escalate_boundary):
        new_definition = SystemEventDefinition()
        new_definition.uframe_filter_id = uframe_filter_id
        new_definition.reference_designator = reference_designator
        new_definition.array_name = array_name
        new_definition.platform_name = platform_name
        new_definition.instrument_name = instrument_name
        new_definition.instrument_parameter = instrument_parameter
        new_definition.instrument_parameter_pdid = instrument_parameter_pdid
        new_definition.operator = operator
        new_definition.created_time = created_time
        new_definition.event_type = event_type
        new_definition.active = active
        new_definition.description = description
        new_definition.high_value = high_value
        new_definition.low_value = low_value
        new_definition.severity = severity
        new_definition.stream = stream
        #,
        #new_definition.escalate_on = escalate_on,
        #new_definition.escalate_boundary = escalate_boundary
        db.session.add(new_definition)
        db.session.commit()
        return
    '''
    @staticmethod
    def delete_system_event_definition(system_event_definition_id):
        status = None
        try:
            if system_event_definition_id is None:
                message = 'system_event_definition id provided is None.'
                print '\n message: ', message
                raise Exception(message)
            definition = db.session.query.get(system_event_definition_id)
            if definition is None:
                message = 'Failed to delete system_event_definition for id provided (id: None)'
                print '\n message: ', message
                raise Exception(message)

            notification = UserEventNotification.query.filter_by(system_event_definition_id=definition.id).first()
            if notification is not None:
                #UserEventNotification.delete_user_event_notification(notification.id)
                db.session.delete(notification)
                db.session.commit()
            db.session.delete(definition)
            db.session.commit()
            return status
        except:
            print '\n (delete_system_event_definition) %s', err.message
            raise

    def to_json(self):
        json_system_event_definition = {
            'id' : self.id,
            'uframe_filter_id': self.uframe_filter_id,
            'reference_designator': self.reference_designator,
            'array_name': self.array_name,
            'platform_name': self.platform_name,
            'instrument_name': self.instrument_name,
            'instrument_parameter': self.instrument_parameter,
            'instrument_parameter_pdid': self.instrument_parameter_pdid,
            'operator': self.operator,
            'created_time': self.created_time,
            'event_type': self.event_type,
            'active': self.active,
            'description': self.description,
            'high_value': self.high_value,
            'low_value': self.low_value,
            'severity': self.severity,
            'stream': self.stream,
            'retired': self.retired,
            'escalate_on': self.escalate_on,
            'escalate_boundary': self.escalate_boundary
        }
        if self.created_time is not None:
            json_system_event_definition['created_time'] = self._pytype(self.created_time)
        if self.ts_retired is not None:
            json_system_event_definition['ts_retired'] = self._pytype(self.ts_retired)
        return json_system_event_definition

    def _pytype(self,v):
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)

class SystemEvent(db.Model):
    """
    Stores the Alert/Alarm instances from uFrame.
    """
    __tablename__ = 'system_events'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    system_event_definition_id = db.Column(db.ForeignKey(u'' + __schema__ + '.system_event_definitions.id'), nullable=False)
    uframe_event_id = db.Column(db.Integer, nullable=False)     # uframe instance id
    uframe_filter_id = db.Column(db.Integer, nullable=False)    # uframe alertfilter id
    event_time = db.Column(db.DateTime(True), nullable=False)   # uframe create time todo - should this be DateTime(False)?
    event_type = db.Column(db.Text, nullable=False)
    event_response = db.Column(db.Text, nullable=False)
    method = db.Column(db.Text, nullable=False)
    deployment = db.Column(db.Integer, nullable=False)
    acknowledged = db.Column(db.Boolean, nullable=False)
    ack_by = db.Column(db.Integer, nullable=True)
    ts_acknowledged = db.Column(db.DateTime(True), nullable=True)
    ticket_id = db.Column(db.Integer, nullable=False, server_default=db.text("0"))	# default = 0; key for redmine ticket; unique identifier to CRUD red mine item.
    escalated = db.Column(db.Boolean, nullable=False, server_default=db.text("false"))   # true when escalate_on time has been reached; once true always true)
    ts_escalated = db.Column(db.DateTime(False), nullable=True) # datetime (date time when first red mine ticket is created)
    timestamp = db.Column(db.DateTime(True), nullable=False)
    ts_start = db.Column(db.DateTime(True), nullable=True)

    event = db.relationship(u'SystemEventDefinition')

    '''
    @staticmethod
    def insert_event(uframe_event_id, uframe_filter_id, system_event_definition_id, event_time, event_type,
                     event_response, method, deployment, ts_acknowledged): #, ticket_id, escalated, ts_escalated):
        new_event = SystemEvent()
        new_event.uframe_event_id = uframe_event_id
        new_event.uframe_filter_id = uframe_filter_id
        new_event.system_event_definition_id = system_event_definition_id
        new_event.event_time = event_time
        new_event.event_type = event_type
        new_event.event_response = event_response
        new_event.method = method
        new_event.deployment = deployment
        new_event.acknowledged = False
        new_event.ack_by = None
        new_event.ts_acknowledged = ts_acknowledged
        #new_event.ticket_id = ticket_id
        #new_event.escalated = escalated
        #new_event.ts_escalated = ts_escalated
        db.session.add(new_event)
        db.session.commit()
        return
    '''
    @staticmethod
    def update_alert_alarm_escalation(id, ticket_id, escalated, ts_escalated):
        try:
            event = SystemEvent.query.get(id)
            if event is None:
                raise Exception('Invalid alert_alarm id, no record found.')
            event.ticket_id = ticket_id
            event.escalated = escalated
            event.ts_escalated = ts_escalated
            db.session.add(event)
            db.session.commit()
            db.session.flush()
            return
        except Exception as err:
            #print '\n debug -- message: ', err.message
            raise

    def to_json(self):
        json_system_event = {
            'id' : self.id,
            'uframe_event_id': self.uframe_event_id,
            'uframe_filter_id': self.uframe_filter_id,
            'system_event_definition_id': self.system_event_definition_id,
            'event_time': self.event_time,
            'event_type': self.event_type,
            'event_response': self.event_response,
            'method': self.method,
            'deployment': self.deployment,
            'acknowledged': self.acknowledged,
            'ack_by': self.ack_by,
            'ticket_id': self.ticket_id,
            'escalated': self.escalated,
        }
        if self.event_time is not None:
            json_system_event['event_time'] = self._pytype(self.event_time)
        if self.ts_acknowledged is not None:
            json_system_event['ts_acknowledged'] = self._pytype(self.ts_acknowledged)
        if self.ts_escalated is not None:
            json_system_event['ts_escalated'] = self._pytype(self.ts_escalated)
        if self.timestamp is not None:
            json_system_event['timestamp'] = self._pytype(self.timestamp)
        if self.ts_start is not None:
            json_system_event['ts_start'] = self._pytype(self.ts_start)
        else:
            json_system_event['ts_start'] = None
        return json_system_event

    def _pytype(self,v):
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)

class TicketSystemEventLink(db.Model):
    __tablename__ = 'ticket_system_event_link'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    system_event_id = db.Column(db.ForeignKey(u'' + __schema__ + '.system_events.id'), nullable=False)
    ticket_id = db.Column(db.Text, nullable=False)

    system_event = db.relationship(u'SystemEvent')

    """
    # todo - Review whether we need this...
    @staticmethod
    def insert_ticket_link():
        usl = TicketSystemEventLink(user_id='1')
        usl.scope_id='1'
        db.session.add(usl)
        db.session.commit()
    """
    @staticmethod
    def insert_ticket_link(system_event_id, ticket_id):
        try:
            new_ticket_system_event = TicketSystemEventLink()
            new_ticket_system_event.system_event_id = system_event_id
            new_ticket_system_event.ticket_id = ticket_id
            db.session.add(new_ticket_system_event)
            db.session.commit()
            db.session.flush()
            return new_ticket_system_event.id
        except Exception as err:
            db.session.rollback()
            #print '\n message: ', err.message
            raise Exception(err.message)


    def to_json(self):
        json_ticket_system_event = {
            'id': self.id,
            'system_event_id': self.system_event_id,
            'ticket_id': self.ticket_id,
        }
        return json_ticket_system_event


class UserEventNotification(db.Model):
    """
    User notification of Alerts/Alarms from uFrame
    """
    __tablename__ = 'user_event_notifications'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    system_event_definition_id = db.Column(db.ForeignKey(u'' + __schema__ + '.system_event_definitions.id'), nullable=False)
    user_id = db.Column(db.ForeignKey(u'' + __schema__ + '.users.id'), nullable=False)
    use_email = db.Column(db.Boolean, nullable=False, server_default=db.text("false"))
    use_redmine = db.Column(db.Boolean, nullable=False, server_default=db.text("true"))
    use_phone = db.Column(db.Boolean, nullable=False, server_default=db.text("false"))
    use_log = db.Column(db.Boolean, nullable=False, server_default=db.text("false"))
    use_sms = db.Column(db.Boolean, nullable=False, server_default=db.text("false"))

    system_event_definition = db.relationship(u'SystemEventDefinition')
    user = db.relationship(u'User')

    def to_json(self):
        json_user_notification = {
            'id': self.id,
            'use_email': self.use_email,
            'use_redmine': self.use_redmine,
            'use_phone': self.use_phone,
            'use_log': self.use_log,
            'use_sms': self.use_sms
        }
        if self.user:
            json_user_notification['user_id'] = self.user.id
        if self.system_event_definition:
            json_user_notification['system_event_definition_id'] = self.system_event_definition.id
        return json_user_notification

    @staticmethod
    def insert_user_event_notification(system_event_definition_id, user_id, use_email, use_redmine, use_phone,
                                        use_log, use_sms):
        user_event_id = None
        try:
            new_user_event_notification = UserEventNotification()
            new_user_event_notification.system_event_definition_id = system_event_definition_id
            new_user_event_notification.user_id = user_id
            new_user_event_notification.use_email = use_email
            new_user_event_notification.use_redmine = use_redmine
            new_user_event_notification.use_phone = use_phone
            new_user_event_notification.use_log = use_log
            new_user_event_notification.use_sms = use_sms
            db.session.add(new_user_event_notification)
            db.session.commit()
            user_event_id = new_user_event_notification.id
            return user_event_id
        except Exception as err:
            db.session.rollback()
            #print '\n (models:insert_user_event_notification) message: ', err.message
            raise Exception(err.message)

    @staticmethod
    def update_user_event_notification(id, system_event_definition_id, user_id,
                                       use_email, use_redmine, use_phone, use_log, use_sms):
        try:
            user_event_notification = UserEventNotification.query.get(id)
            if user_event_notification is None:
                raise Exception('Invalid ID, user_event_notification record not found')
            user_event_notification.system_event_definition_id = system_event_definition_id
            user_event_notification.user_id = user_id
            user_event_notification.use_email = use_email
            user_event_notification.use_redmine = use_redmine
            user_event_notification.use_phone = use_phone
            user_event_notification.use_log = use_log
            user_event_notification.use_sms = use_sms
            db.session.add(user_event_notification)
            db.session.commit()
            return
        except Exception as err:
            db.session.rollback()
            message = 'debug -- Models (update_user_event_notification) %s', err.message
            #print '\n message: ', message
            raise Exception(err.message)

    '''
    @staticmethod
    def delete_user_event_notification(user_event_notification_id):
        status = None
        try:
            if user_event_notification_id is None:
                message = 'user_event_notification_id id provided is None.'
                print '\n message: ', message
                raise Exception(message)
            notification = UserEventNotification.query.get(user_event_notification_id)
            if notification is not None:
                db.session.delete(notification)
                db.session.commit()
        except:
            print '\n (delete_user_event_notification) %s', err.message
            raise
    '''

class UserScopeLink(db.Model):
    __tablename__ = 'user_scope_link'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey(u'' + __schema__ + '.users.id'), nullable=False)
    scope_id = db.Column(db.ForeignKey(u'' + __schema__ + '.user_scopes.id'), nullable=False)

    scope = db.relationship(u'UserScope')
    user = db.relationship(u'User')

    @staticmethod
    def insert_scope_link():
        usl = UserScopeLink(user_id='1')
        usl.scope_id='1'
        db.session.add(usl)
        db.session.commit()

    def to_json(self):
        json_scope_link = {
            'id' : self.id,
            'user_id' : self.user_id,
            'scope_id' : self.scope_id,
        }
        return json_scope_link

    def __repr__(self):
        return '<User %r, Scope %r>' % (self.user_id, self.scope_id)



class UserScope(db.Model, DictSerializableMixin):
    __tablename__ = 'user_scopes'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    scope_name = db.Column(db.Text, nullable=False, unique=True)
    scope_description = db.Column(db.Text)

    @staticmethod
    def insert_scopes():
        scopes = {
            'redmine',
            'asset_manager',
            'user_admin',
            'annotate',
            'command_control',
            'organization'
            }
        for s in scopes:
            scope = UserScope.query.filter_by(scope_name=s).first()
            if scope is None:
                scope = UserScope(scope_name=s)
            db.session.add(scope)
        db.session.commit()

    def to_json(self):
        json_scope = {
            'id' : self.id,
            'scope_name' : self.scope_name,
            'scope_description' : self.scope_description,
        }
        return json_scope

    def __repr__(self):
        return '<Scope ID: %r, Scope Name: %s>' % (self.id, self.scope_name)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    __table_args__ = {u'schema': __schema__}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Text, unique=True, nullable=False)
    pass_hash = db.Column(db.Text)
    email = db.Column(db.Text, unique=True, nullable=False)
    user_name = db.Column(db.Text, unique=True, nullable=False)
    active = db.Column(db.Boolean, nullable=False, server_default=db.text("false"))
    confirmed_at = db.Column(db.Date)
    first_name = db.Column(db.Text)
    last_name = db.Column(db.Text)
    phone_primary = db.Column(db.Text)
    phone_alternate = db.Column(db.Text)
    role = db.Column(db.Text)
    organization_id = db.Column(db.ForeignKey(u'' + __schema__ + '.organizations.id'), nullable=False)
    scopes = db.relationship(u'UserScope', secondary=UserScopeLink.__table__)
    organization = db.relationship(u'Organization')
    watches = db.relationship(u'Watch')

   # def __init__(self, **kwargs):
   #     super(User, self).__init__(**kwargs)
   #         self.scope = Scope.query.filter_by(scope_name='user_admin').first()
   #         if self.scope is None:
   #             self.scope = Role.query.filter_by(default=True).first()

    def to_json(self):
        json_user = {
            'id' : self.id,
            'user_id' : self.user_id,
            'email' : self.email,
            'active' : self.active,
            'first_name' : self.first_name,
            'active' : self.active,
            'last_name' : self.last_name,
            'phone_primary' : self.phone_primary,
            'phone_alternate' : self.phone_alternate,
            'role' : self.role,
            'organization_id' : self.organization_id,
            'scopes' : [s.scope_name for s in self.scopes],
            'user_name' : self.user_name
        }
        if self.organization:
            json_user['organization'] = self.organization.organization_name
        return json_user

    @staticmethod
    def from_json(json):
        email = json.get('email')
        password = json.get('password')
        password2 = json.get('repeatPassword')
        phone_primary = json.get('primary_phone')
        user_name = json.get('username')
        first_name = json.get('first_name')
        last_name = json.get('last_name')
        role = json.get('role_name')
        organization_id = json.get('organization_id')

        #Validate some of the field.

        new_user = User()
        new_user.validate_email(email)
        new_user.validate_username(user_name)
        new_user.validate_password(password, password2)
        pass_hash = generate_password_hash(password)
        #All passes, return the User object ready to be stored.
        return User(email=email,
                    pass_hash=pass_hash,
                    phone_primary=phone_primary,
                    user_name=user_name,
                    user_id=user_name,
                    first_name=first_name,
                    last_name=last_name,
                    organization_id=organization_id,
                    role=role)


    @staticmethod
    def insert_user(username='admin', password=None, first_name='First', last_name='Last', email='FirstLast@somedomain.com', org_name='RPS ASA', phone_primary='8001234567'):
        user = User(password=password, first_name=first_name, active=True)
        user.validate_username(username)
        user.validate_email(email)
        user.user_name = username
        user.email = email
        user.user_id = username
        user.last_name = last_name
        user.phone_primary = phone_primary
        org = Organization.query.filter(Organization.organization_name == org_name).first()
        user.organization_id = org.id
        db.session.add(user)
        db.session.commit()

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    #Store the hashed password.
    @password.setter
    def password(self, password):
        self.pass_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.pass_hash, password)

    def validate_email(self, field):
        if User.query.filter_by(email=field).first():
            raise ValidationError('Email already in use.')

    def validate_username(self, field):
        if User.query.filter_by(user_name=field).first():
            raise ValidationError('User name already taken.')

    def validate_password(self, password, password2):
        temp_hash = User(password=password)
        if not temp_hash.verify_password(password2):
            raise ValidationError('Passwords do not match')

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'], expires_in=expiration)
        return s.dumps({'id': self.id})

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    def can(self, scope):
        #db.session.query
        return scope in [s.scope_name for s in self.scopes]

    def __repr__(self):
        return '<User: %r, ID: %r>' % (self.user_name, self.id)



class Watch(db.Model, DictSerializableMixin):
    __tablename__ = 'watches'
    __table_args__ = {u'schema' : __schema__}

    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    user_id = db.Column(db.ForeignKey(u'' + __schema__ + '.users.id'), nullable=False)

    user = db.relationship(u'User')
    operator_events = db.relationship(u'OperatorEvent')

    def to_json(self):
        data = self.serialize()
        del data['user_id']
        data['user'] = {
            'first_name': self.user.first_name,
            'last_name' : self.user.last_name,
            'email' : self.user.email
        }
        return data


    @staticmethod
    def from_json(json_post):
        id = json_post.get('id')
        start_time = json_post.get('start_time')
        end_time = json_post.get('end_time')
        user_id = json_post.get('user_id')
        return Watch(id=id, start_time=start_time, end_time=end_time, user_id=user_id)
