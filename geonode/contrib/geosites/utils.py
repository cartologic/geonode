# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2016 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

import os
import shutil
from django.contrib.sites.models import Site
from django.conf import settings
from .models import SiteResources, SitePeople, SiteGroups
from django.core import serializers

def resources_for_site():
    return SiteResources.objects.get(site=Site.objects.get_current()).resources.all()


def users_for_site():
    return SitePeople.objects.get(site=Site.objects.get_current()).people.all()


def groups_for_site():
    return SiteGroups.objects.get(site=Site.objects.get_current()).group.all()


def sed(filename, change_dict):
    """ Update file replacing key with value in provided dictionary """
    f = open(filename, 'r')
    data = f.read()
    f.close()

    for key, val in change_dict.items():
        data = data.replace(key, val)

    f = open(filename, 'w')
    f.write(data)
    f.close()


def dump_model(model, filename):
    from django.core import serializers
    data = serializers.serialize("json", model.objects.all(), indent=4)
    f = open(filename, "w")
    f.write(data)
    f.close()


def add_site(name, domain):
    """ Add a site to database, create directory tree """

    # get latest SITE id
    sites = Site.objects.all()
    used_ids = [v[0] for v in sites.values_list()]
    site_id = max(used_ids) + 1

    # current settings is one of the sites
    project_dir = os.path.realpath(os.path.join(settings.SITE_ROOT, '../'))
    site_dir = os.path.join(project_dir, 'site%s' % site_id)
    site_template = os.path.join(os.path.dirname(__file__), 'site_template')
    shutil.copytree(site_template, site_dir)

    # update configuration and settings files
    change_dict = {
        '$SITE_ID': str(site_id),
        '$SITE_NAME': name,
        '$DOMAIN': domain,
        '$SITE_ROOT': site_dir,
        '$SERVE_PATH': settings.SERVE_PATH,
        '$PORTNUM': '8%s' % str(site_id).zfill(3),
        '$GEOSERVER_URL': settings.GEOSERVER_URL,
        '$PROJECT_NAME': os.path.basename(os.path.dirname(settings.PROJECT_ROOT)),
    }

    sed(os.path.join(site_dir, 'conf/gunicorn'), change_dict)
    sed(os.path.join(site_dir, 'conf/nginx'), change_dict)
    sed(os.path.join(site_dir, 'settings.py'), change_dict)
    sed(os.path.join(site_dir, 'local_settings_template.py'), change_dict)
    sed(os.path.join(site_dir, 'wsgi.py'), change_dict)

    # add site to database
    site = Site(id=site_id, name=name, domain=domain)
    site.save()
    dump_model(Site, os.path.join(project_dir, 'sites.json'))


def dump_bulk_tree( qset,parent=None, keep_ids=True):
        """Dumps a tree branch to a python data structure."""
        
        ret, lnk = [], {}
        for pyobj in qset:
            serobj = serializers.serialize('python', [pyobj])[0]
            # django's serializer stores the attributes in 'fields'
            fields = serobj['fields']
            depth = fields['depth'] or 1
            fields['text'] = fields['name']
            fields['href'] = fields['slug']
            del fields['name']
            del fields['slug']
            del fields['path']
            del fields['numchild']
            del fields['depth']
            if 'id' in fields:
                # this happens immediately after a load_bulk
                del fields['id']

            newobj = {}
            for field in fields:
                newobj[field] = fields[field]
            if keep_ids:
                newobj['id'] = serobj['pk']

            if (not parent and depth == 1) or\
               (parent and depth == parent.depth):
                ret.append(newobj)
            else:
                parentobj = pyobj.get_parent()
                parentser = lnk[parentobj.pk]
                if 'nodes' not in parentser:
                    parentser['nodes'] = []
                parentser['nodes'].append(newobj)
            lnk[pyobj.pk] = newobj
        return ret