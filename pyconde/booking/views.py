# Create your views here.
from django.core.mail import send_mail
from django.db.models import Sum

from django.shortcuts import render_to_response, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.context_processors import csrf
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

from pyconde.accounts.models import Profile

from django.template import RequestContext
from django.contrib.auth import authenticate, login, logout

from .models import Workshop, Workshopper
from . import utils

import sys

def index(request):
    context  = {
        "workshops":Workshop.objects.order_by("item__start"),
        }
    return render_to_response("booking/booking_index.html",
                              context,
                              context_instance=RequestContext(request))


def book(request):

    if not request.user.is_authenticated():
        context  = {
            "workshops":Workshop.objects.order_by("item__start"),
            }
        return render_to_response("booking/booking_index.html",
                                  context,
                                  context_instance=RequestContext(request))
    try:
        workshopper = request.user.workshopper_profile
    except:
        return render_to_response("booking/notaworkshopper.html",
                                  {},
                                  context_instance=RequestContext(request))
                                  
    if request.method == "POST":
        # handle the action - book or unbook
        if request.POST['action']=="book":
            msg = utils.bookSession(request.user, request.POST['workshop'])
            messages.add_message(request, messages.INFO,msg)
        elif request.POST['action']=="unbook":
            msg = utils.unbookSession(request.user, request.POST['workshop'])
            messages.add_message(request, messages.INFO,msg)
        else:
            messages.add_message(request,messages.INFO, "Unrecognised action")
        return HttpResponseRedirect("")
    else:
        pass

    workshopper = request.user.workshopper_profile
    credits_left = workshopper.credits_left()
    
    workshops = Workshop.objects.select_related().order_by("item__start")

    for w in workshops:
        w.spaceclassX = w.spaceclass()

    booked = workshopper.booked.all()

    utils.addstates(workshopper, booked,  workshops)

    context = {
        "funds": credits_left,
        "workshops": workshops
        }
    return render_to_response("booking/booking_book.html",
                              context,
                              context_instance=RequestContext(request))

@login_required
def summary(request):

    try:
        workshopper = request.user.workshopper_profile
    except:
        return render_to_response("booking/notaworkshopper.html",
                                  {},
                                  context_instance=RequestContext(request))

    workshopper = request.user.workshopper_profile
    ctx = {
        "workshopper":workshopper,
        "credits_left":  workshopper.credits_left(),
        "booked": workshopper.booked.all()
        }
    return render_to_response("booking/booking_summary.html",
                              ctx,
                              context_instance=RequestContext(request))

def login_user(request):
    if request.method=="POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect(".")
            else:
                messages.add_message(request,messages.INFO, "Account disabled")
                return HttpResponseRedirect("login")
        else:
            messages.add_message(request,messages.INFO, "Invalid login/pass")
            return HttpResponseRedirect("login")
    else:
        return render_to_response("booking/login.html",
                                  {},
                                  context_instance=RequestContext(request))

def logout_user(request):
    logout(request)
    return HttpResponseRedirect(".")

from django.db import IntegrityError, transaction

@permission_required('booking.add_booking')
def bookreport(request):
    workshops = Workshop.objects.select_related().order_by("item__start")
    return render_to_response('booking/bookreport.html',
                              {'workshops': workshops},
                              context_instance=RequestContext(request))

@staff_member_required
def refundreport(request):
    ws=Workshopper.objects.select_related(depth=2).annotate(spending=Sum("booked__cost"))
    refunds = [w for w in ws if not w.spending]
    for w in refunds:
        w.spending=0
    refunds.extend([w for w in ws if w.spending and w.spending<w.credits])
    daycost = 75
    totalGenerous = 0
    totalDay = 0
    totalHalf = 0
    for w in refunds:
        unspent = w.credits - w.spending
        # round it to nearest 4 for day
        w.unspentDay = 4 * (int(unspent)/int(4))
        w.unspentHalf = 2 * (int(unspent)/int(2))
        w.amountHalf = float(daycost)*(float(w.unspentHalf)/float(4))
        w.amountDay = float(daycost)*(float(w.unspentDay)/float(4))
        w.amountGenerous = float(daycost) * (float(w.credits) - float(w.spending))/float(4)
        totalHalf = totalHalf + w.amountHalf
        totalDay = totalDay + w.amountDay
        totalGenerous = totalGenerous + w.amountGenerous
    refunds.sort(key=lambda x: x.user.last_name)
    return render_to_response("booking/refundreport.html",
                              {'refunds': refunds,
                               'totalGenerous': totalGenerous,
                               'totalDay': totalDay,
                               'totalHalf': totalHalf,
                               'daycost': daycost},
                              context_instance=RequestContext(request))
    pass

@staff_member_required
def secretbookreport(request):
    """ an unprotected booking report, to be accessed via an obscure URL 
    security through obscurity. Yes. """

    workshops = Workshop.objects.select_related().order_by("item__start")
    return render_to_response('booking/simplereport.html',
                              {'workshops': workshops},
                              context_instance=RequestContext(request))

@staff_member_required
def registrationreport(request):
    """ produce a report for the registration desk
    for each half day, list people expected
    order by surname
    list workshops they are going to
    """
    who = Workshopper.objects.all()
    byday = daytable(who)
    return render_to_response('booking/regreport.html',
                              {'byday': byday},
                              context_instance=RequestContext(request))

@staff_member_required
def secretspending(request):
    """ return who has spent all/some/none of their credits """
    
    ws=Workshopper.objects.select_related(depth=2).annotate(spending=Sum("booked__cost"))

    spentNone = [w for w in ws if not w.spending]
    spentAll = [w for w in ws if w.spending==w.credits]
    spentSome = [w for w in ws if w.spending and w.spending<w.credits]

    return render_to_response("booking/spenders.html",
                              {'some': spentSome,
                               'none': spentNone,
                               'all': spentAll},
                              context_instance=RequestContext(request))

from collections import defaultdict
def daytable(wshoppers):
    d = defaultdict( list )
    for who in wshoppers:
        for wshop in who.booked.all():
            d[wshop.item.start.date()].append(who)
    return [{k:surnamesort(list(set(d[k])))} for k in sorted(d) ]
            

def lastnamesort(w):
    return w.user.last_name

def surnamesort(w):
    return sorted(w,key=lastnamesort)

@transaction.commit_on_success
@permission_required('booking.add_booking')
def add_workshopper(request):
    if request.method == "POST":
        sendmail = request.POST.has_key('sendmail')
        email = request.POST['email']

        usersWithThat = User.objects.filter(email=email)
        nwithemail = usersWithThat.count()
        if nwithemail > 0:
            return render_to_response("booking/emailexists.html",
                                      {'email': email,
                                       'who': usersWithThat},
                                      context_instance=RequestContext(request))
        
        clearpass = request.POST['pass']
        password = make_password(clearpass)
        newU = User(
            password = password,
            email = email,
            first_name = request.POST['firstname'],
            last_name = request.POST['lastname']
            )
        try:
            newU.save()
            username = "delegate"+str(newU.pk)
            newU.username=username
            newU.save()
        except:
            e = str(sys.exc_info()[1])
            print e
            html = "<html><body><p>Error: %s creating User</p></body></html>" % e
            return render_to_response("booking/booking_adderror.html",
                                      {'error': e},
                                      context_instance=RequestContext(request))
        credits = int(request.POST['credits'])
        newP = Profile(user=newU)
        newP.save()
        newW = Workshopper(user=newU, credits=credits)
        newW.save()
        messages.add_message(request,messages.INFO, "Workshopper "+newU.username+" created")
        if sendmail:
            msg = """

Your account for booking workshop sessions for FOSS4G2013 has been created.

Please go to http://2013.foss4g.org/conf/booking and log in as:

Username: %s
Password: %s

""" % (username, clearpass)
            send_mail("FOSS4G2013 Workshop Booking",msg,'info@2013.foss4g.org',[email],fail_silently=False)
            messages.add_message(request,messages.INFO, "Email sent")
        return HttpResponseRedirect("")

    initp = utils.randompass()
    return render_to_response("booking/add_ws.html",{'initp':initp},context_instance=RequestContext(request))
