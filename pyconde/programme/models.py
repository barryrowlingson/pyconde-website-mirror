from django.db import models

# Create your models here.
from pyconde.conference import models as conference_models
from pyconde.tagging import TaggableManager
from tinymce import models as tinymce_models
from django.template.loader import render_to_string
import datetime

class Person(models.Model):
    name = models.CharField(max_length=100)
    affiliation = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    contact = models.TextField(blank=True)
    biog = tinymce_models.HTMLField(blank=True)    
    notes = models.TextField("Committee use only",blank=True)

    def __unicode__(self):
        return self.name

class PSession(models.Model):
    chair = models.ForeignKey(Person, blank=True, null=True,related_name="chairperson")
    helper = models.ForeignKey(Person, blank=True, null=True,related_name="helper")
    start = models.DateTimeField()
    location = models.ForeignKey(conference_models.Location,blank=True, null=True)
    talkduration = models.IntegerField("minutes per talk")
    slotcount = models.IntegerField("how many talks in this?")
    title = models.CharField(max_length=200)
    tags = TaggableManager(blank=True)
    notes = models.TextField("Committee use only",blank=True)

    class Meta:
        verbose_name="Presentation Session"

    def end(self):
        return self.start + datetime.timedelta(minutes=self.talkduration)*self.slotcount

    def __unicode__(self):
        if self.location:
            return u"%s: %s talks in %s at %s " % (self.title,self.slotcount,self.location, self.start)
        else:
            return u"%s: %s talks at %s in unassigned room" % (self.title,self.slotcount,self.start)


class Presentation(models.Model):
    presenter = models.ForeignKey(Person, related_name="presenter")
    copresenter = models.ManyToManyField(Person, blank=True, null=True)
    title = models.CharField(max_length=200)
    desc = models.TextField()
    abstract = tinymce_models.HTMLField()    
    insession = models.ForeignKey(PSession, blank=True, null=True)
    position = models.IntegerField(blank=True, null=True)
    tags = TaggableManager(blank=True)
    notes = models.TextField("Committee use only",blank=True)
    cancelled = models.BooleanField(default=False)

    @property
    def start(self):
        if self.insession:
            return self.insession.start + (self.position-1)*datetime.timedelta(minutes=self.insession.talkduration)
        else:
            return None
    @property
    def end(self):
        return self.start + datetime.timedelta(minutes = self.insession.talkduration)

    def cellValue(self):
        contents = render_to_string("programme/presentation_cell.html",{'pres':self})
        if self.position == 1:
            stitle = render_to_string("programme/session_head.html",{'s':self.insession})
            contents = '%s %s' % (stitle,contents)
            klass="first"
        else:
            klass="next"
        if self.show:
            klass = klass + " feature"
        return {'content':"%s" % contents,
                'class':"presentation %s" % klass
                }

    def __unicode__(self):
        return u"%s (%s)" % (self.title, self.presenter)

class CWorkshop(models.Model):
    """ a free community workshop """
    title = models.CharField("Workshop title",max_length=200)
    presenter = models.ForeignKey(Person, related_name="cw_presenter")
    copresenter = models.ManyToManyField(Person, blank=True, null=True, related_name="cw_copresenter")
    helper = models.ForeignKey(Person, blank=True, null=True,related_name="community_helper", help_text="FOSS4G Volunteer")
    start = models.DateTimeField("Start date/time")
    desc = models.TextField("Description")
    location = models.ForeignKey(conference_models.Location,blank=True, null=True)
    maxdelegates = models.IntegerField("Max delegates - may also be limited by room")
    duration = models.IntegerField("Duration in minutes")
    notes = models.TextField("Committee use only")

    def capacity(self):
        return min(self.maxdelegates, self.location.capacity)

    def __unicode__(self):
        return u"%s (%s)" % (self.title, self.presenter)

    class Meta:
        verbose_name="Free Workshop"
    
    def end(self):
        return self.start + datetime.timedelta(minutes=self.duration)

class PlenarySession(models.Model):
    """PlenarySession objects are containers for plenary sessions,
    when we all get together and there's a few items for business.
    It has no location because it happens in all the plenary places."""
    start = models.DateTimeField()
    duration = models.IntegerField("Duration in minutes")
    title = models.CharField(max_length=100)
    def end(self):
        return self.start + datetime.timedelta(minutes=self.duration)
    def cellValue(self):
        contents = render_to_string("programme/plenary_cell.html",{'plenary': self})
        return {'content': contents,
                'class': "plenary"
                }
                                    
    def __unicode__(self):
        return u"%s" % (self.title)

class PlenaryItem(models.Model):
    """A PlenaryItem is within a PlenarySession. Timings may be approximate"""
    title = models.CharField(max_length=200)
    session = models.ForeignKey(PlenarySession, blank=True, null=True)
    position = models.IntegerField("Position in session", blank=True, null=True)
    duration = models.IntegerField("Time for this, in minutes")
    details = tinymce_models.HTMLField(blank=True, null=True)
    link = models.URLField("Link if NO details",blank=True,null=True)
    def __unicode__(self):
        return u"%s" % (self.title)

class GlobalEvent(models.Model):
    """ A GlobalEvent happens everywhere, like lunch or coffee breaks, or parties """
    name = models.CharField(max_length=200)
    start = models.DateTimeField()
    duration = models.IntegerField("Duration in minutes")
    details = tinymce_models.HTMLField(blank=True, null=True)
    link = models.URLField("Link if NO details",blank=True,null=True)
    def end(self):
        return self.start + datetime.timedelta(minutes=self.duration)
    def cellValue(self):
        contents = render_to_string("programme/global_cell.html",{'event': self})
        return {'content': contents,
                'class': "global"
                }
  
    def __unicode__(self):
        return "%s" % (self.name)

class SpecialEvent(models.Model):
    """ These are highlighted on the day of the programme, eg unconference, map gallery """
    name = models.CharField(max_length=200)
    details = tinymce_models.HTMLField(blank=True, null=True)
    link = models.URLField("Optional Main Link",blank=True,null=True)
    start = models.DateField() # give full timing details in link or details
    location = models.CharField(max_length=200) # could be anywhere...
    def __unicode__(self):
        return "%s" % (self.name)

class Keynote(models.Model):
    """ probably not using this now..."""
    speaker = models.ForeignKey(Person)
    title = models.CharField(max_length=200)
    abstract = tinymce_models.HTMLField()
    notes = models.TextField("Committee use only",blank=True)
    cancelled = models.BooleanField(default=False)
    tags = TaggableManager(blank=True)

    def __unicode__(self):
        return u"%s (%s)" % (self.title, self.speaker)


class Volunteering(models.Model):
    """ Records volunteer activities except session helping/chairing """
    title = models.CharField(max_length=200)
    start = models.DateTimeField("Start time")
    needed = models.IntegerField("How many needed?")
    duration = models.IntegerField("Duration in minutes")                             
    description = models.TextField("Describe the activity",blank=True)
    notes = models.TextField("Committee use only",blank=True)
    volunteer = models.ManyToManyField(Person,related_name="volunteer")

    def end(self):
        return self.start + datetime.timedelta(minutes=self.duration)

    def totalvolunteers(self):
        return self.volunteer.count()
    def state(self):
        n = self.volunteer.count()
        needed = self.needed
        if n == needed:
            return "Complete"
        if n < needed:
            return "Need more"
        return "Overfull"
    def __unicode__(self):
        return u"%s" % self.title
