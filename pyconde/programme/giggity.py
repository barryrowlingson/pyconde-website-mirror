#
# write giggity-compatible format file
#

from . import models
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.conf import settings

import codecs

PRES_ID=10000
PLENARY_ID=20000
EVENT_ID=30000

def make_ical():
    P = models.Presentation.objects.filter(insession__gt=0).order_by("insession").prefetch_related("presenter","copresenter")
    for p in P:
        p.UID=p.pk+PRES_ID
        p.DTSTART = p.start.strftime("%Y%m%dT%H%M%SZ")
        p.DTEND = p.end.strftime("%Y%m%dT%H%M%SZ")
        p.SUMMARY = p.title
        p.LOCATION = p.insession.location
        p.DESCRIPTION = p.presenter
        p.URL = "http://2013.foss4g.org/p/%s" % p.pk
        p.ROOMNAME = slugify(p.LOCATION)
    return render_to_string("giggity/ical.template",{'presentations': P})

def make_xml():
        P = models.Presentation.objects.filter(insession__gt=0).order_by("insession").prefetch_related("presenter","copresenter").select_related("tags")
        #newb = models.Tag.objects.get(name="newbie")
        for p in P:
            #p.newb = newb in p.tags.all()
            p.UID=p.pk+PRES_ID
            p.DTSTART = p.start.strftime("%Y%m%dT%H%M%SZ")
            p.DTEND = p.end.strftime("%Y%m%dT%H%M%SZ")
            p.SUMMARY = p.title
            p.LOCATION = p.insession.location
            p.DESCRIPTION = p.presenter
            p.URL = "http://2013.foss4g.org/p/%s" % p.pk
            p.ROOMNAME = slugify(p.LOCATION)
            p.duration = (p.end - p.start).seconds/60
        Phash = dict((p.id, p) for p in P)
        S = models.PSession.objects.all().prefetch_related("location","presentation_set")
        
        for s in S:
            s.day = (s.start.date()- settings.FIRST_DAY).days + 1

        Ss = sorted(S,key=lambda x: (x.day,x.location_id))

        plenaries = models.PlenarySession.objects.all().select_related(depth=2)
        for plenary in plenaries:
            plenary.day = (plenary.start.date() - settings.FIRST_DAY).days + 1
            duration = (plenary.end() - plenary.start).seconds/60
            hrs = duration / 60
            mins = duration % 60
            plenary.duration = "%02d:%02d" % (hrs,mins)
            plenary.items = plenary.plenaryitem_set.all().order_by("position")
            plenary.pid = 5000+plenary.pk
            
        context = {"Phash": Phash,
                   "S": Ss,
                   "plenaries":plenaries}
        return render_to_string("giggity/schedule.xml",
                                context,
                                )

def writeXML(filepath):
    f=codecs.open(filepath,encoding="utf-8",mode="w")
    xml = make_xml()
    f.write(xml)
    f.close()
