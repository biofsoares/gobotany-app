import string
from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.template import RequestContext
from gobotany.core import botany
from gobotany.core.models import GlossaryTerm, Pile, PileGroup, Genus, Family
from gobotany.core.models import Taxon, TaxonCharacterValue, Lookalike
from gobotany.simplekey.models import Page, get_blurb


def get_simple_url(item):
    """Return the URL to where `item` lives in the Simple Key navigation."""
    if isinstance(item, Page):
        return item.get_absolute_url()
    if isinstance(item, PileGroup):
        return reverse('gobotany.simplekey.views.pilegroup_view',
                       kwargs={'pilegroup_slug': item.slug})
    elif isinstance(item, Pile):
        return reverse('gobotany.simplekey.views.results_view',
                       kwargs={'pilegroup_slug': item.pilegroup.slug,
                               'pile_slug': item.slug})
    else:
        raise ValueError('the Simple Key has no URL for %r' % (item,))


def index_view(request):
    blurb = get_blurb('getting_started')
    c = request.COOKIES.get('skip_getting_started', '')
    skip_getting_started = (c == 'skip')
    if skip_getting_started and request.GET.get('skip') != 'no':
        return redirect('1/')
    return render_to_response('simplekey/index.html', {
            'blurb': blurb,
            'skip_getting_started': skip_getting_started,
            }, context_instance=RequestContext(request))


def map_view(request):
    return render_to_response('simplekey/map.html', {
            'pages': Page.objects.order_by('number').all(),
            }, context_instance=RequestContext(request))


def glossary_view(request, letter):
    glossary = GlossaryTerm.objects.filter(visible=True).extra(
        select={'lower_term': 'lower(term)'}).order_by('lower_term')
    if letter == '1':
        # All terms whose names start with a number.
        glossary = glossary.filter(term__gte='1', term__lte='9z')
    else:
        glossary = glossary.filter(term__startswith=letter)
    # Case-insensitive sort
    return render_to_response('simplekey/glossary.html', {
            'this_letter': letter,
            'letters': '1' + string.ascii_lowercase,
            'glossary': glossary,
            }, context_instance=RequestContext(request))


def guided_search_view(request):
    return render_to_response('simplekey/guided_search.html', {
            }, context_instance=RequestContext(request))

def page_view(request, number):
    try:
        number = int(number)
    except ValueError:
        raise Http404
    page = get_object_or_404(Page, number=number)
    return render_to_response('simplekey/page.html', {
            'page': page,
            'pilegroups_and_urls': [
                (pilegroup, get_simple_url(pilegroup))
                for pilegroup in page.pilegroups.order_by('id').all()
                ]
            }, context_instance=RequestContext(request))


def pilegroup_view(request, pilegroup_slug):
    pilegroup = get_object_or_404(PileGroup, slug=pilegroup_slug)
    return render_to_response('simplekey/pilegroup.html', {
            'pilegroup': pilegroup,
            'piles_and_urls': [
                (pile, get_simple_url(pile))
                for pile in pilegroup.piles.order_by('slug').all()
                ]
            }, context_instance=RequestContext(request))


def results_view(request, pilegroup_slug, pile_slug):
    pile = get_object_or_404(Pile, slug=pile_slug)
    if pile.pilegroup.slug != pilegroup_slug:
        raise Http404
    return render_to_response('simplekey/results.html', {
           'pilegroup': pile.pilegroup,
           'pile': pile,
           }, context_instance=RequestContext(request))


def _get_states_status(taxon):
    DEFAULT_STATUS = 'absent'
    STATES = ['CT', 'MA', 'ME', 'NH', 'RI', 'VT']
    status = dict().fromkeys(STATES, DEFAULT_STATUS)
    # If the taxon is present in a state, set its status as such.
    distribution = []
    if taxon.distribution:
        distribution = taxon.distribution.replace(' ', '').split('|')
    for state in distribution:
        if status.has_key(state):
            status[state] = 'present'
    # Add any conservation status information for each state.
    for state in STATES:
        # Check the appropriate taxon field.
        status_field_name = 'conservation_status_%s' % state.lower()
        conservation_status = getattr(taxon, status_field_name)
        if conservation_status:
            if conservation_status == 'E':
                conservation_status = 'endangered'
            elif conservation_status == 'T':
                conservation_status = 'threatened'
            elif conservation_status == 'SC' or conservation_status == 'SC*':
                conservation_status = 'special concern'
            elif conservation_status == 'H':
                conservation_status = 'historic'
            elif conservation_status == 'X':
                conservation_status = 'extinct'
            elif conservation_status == 'C':
                conservation_status = 'rare'
            status[state] = conservation_status
    # Add any invasive status information.
    invasive_states = []
    if taxon.invasive_in_states:
        invasive_states = taxon.invasive_in_states.replace(' ', '').split('|')
    for state in invasive_states:
        if status.has_key(state):
            status[state] = 'invasive'
    # Add any sale-prohibited status information, which trumps invasive
    # status that may have just been set.
    prohibited_states = []
    if taxon.sale_prohibited_in_states:
        prohibited_states = \
            taxon.sale_prohibited_in_states.replace(' ', '').split('|')
    for state in prohibited_states:
        if status.has_key(state):
            status[state] = 'prohibited'
    return status


def _get_species_characteristics(pile, taxon):
    characteristics = []
    # Get all the character values for this taxon.
    cvs = TaxonCharacterValue.objects.filter(taxon=taxon)
    if cvs:
        #for filter in pile.default_filters.all():
        for character in pile.plant_preview_characters.all():
            i = 0
            found = False
            value = ''
            while found == False and i < len(cvs):
                if cvs[i].character_value.character.short_name == \
                   character.short_name:
                    found = True
                    if (character.value_type == 'TEXT'):
                        value = cvs[i].character_value.value_str
                    else:
                        # TODO: Properly handle numeric values and units.
                        #value = cvs[i].character_value.value_str
                        value = '%s (mm?) - %s (mm?)' % \
                            (str(cvs[i].character_value.value_min),
                            str(cvs[i].character_value.value_max))
                i = i + 1
            characteristic = {}
            characteristic['name'] = character.name
            characteristic['value'] = value
            characteristics.append(characteristic)
    return characteristics


def _get_wetland_status(status_code):
    '''
    Return plain language text for a wetland status code.
    '''
    status = 'not classified'
    if status_code == 'FAC' or status_code == 'FAC+' or status_code == 'FAC-':
        status = 'Occurs in wetlands or uplands.'
    elif status_code == 'FACU':
        status = 'Usually occurs in uplands, but occasionally occurs in ' \
                 'wetlands.'
    elif status_code == 'FACU+':
        status = 'Occurs most often in uplands; rarely in wetlands.'
    elif status_code == 'FACU-':
        status = 'Usually occurs in uplands, but occurs in wetlands more ' \
                 'than occasionally.'
    elif status_code == 'FACW':
        status = 'Usually occurs in wetlands, but occasionally occurs in ' \
                 'non-wetlands.'
    elif status_code == 'FACW+':
        status = 'Occurs most often in wetlands; rarely in non-wetlands.'
    elif status_code == 'FACW-':
        status = 'Occurs in wetlands but also occurs in uplands more than ' \
                 'occasionally.'
    elif status_code == 'OBL':
        status = 'Occurs only in wetlands.'
    elif status_code == 'UPL':
        status = 'Never occurs in wetlands.'
    return status


def species_view(request,  genus_slug, specific_epithet_slug,
                 pilegroup_slug=None, pile_slug=None):
    scientific_name = '%s %s' % (genus_slug.capitalize(), 
                                 specific_epithet_slug)
    taxa = Taxon.objects.filter(scientific_name=scientific_name)
    if not taxa:
        raise Http404
    taxon = taxa[0]
    
    if pile_slug and pilegroup_slug:
        pile = get_object_or_404(Pile, slug=pile_slug)
        if pile.pilegroup.slug != pilegroup_slug:
            raise Http404
    else:
        # Get the first pile from the species
        pile = taxon.piles.all()[0]
    pilegroup = pile.pilegroup
    
    species_images = botany.species_images(taxon)
    states_status = _get_states_status(taxon)
    habitats = []
    if taxon.habitat:
        habitats = taxon.habitat.split('|')
    lookalikes = Lookalike.objects.filter(scientific_name=scientific_name)
    return render_to_response('simplekey/species.html', {
           'pilegroup': pilegroup,
           'pile': pile,
           'scientific_name': scientific_name,
           'taxon': taxon,
           'species_images': species_images,
           'states_status': states_status,
           'habitats': habitats,
           'characteristics': _get_species_characteristics(pile, taxon),
           'wetland_status': _get_wetland_status(taxon.wetland_status),
           'lookalikes': lookalikes,
           }, context_instance=RequestContext(request))


def genus_view(request, genus_slug):
    genus = get_object_or_404(Genus, slug=genus_slug.lower())
    genus_images = genus.images.filter(image_type__name='example image')
    genus_drawings = genus.images.filter(image_type__name='example drawing')
    return render_to_response('simplekey/genus.html', {
           'item': genus,
           'item_images': genus_images,
           'item_drawings': genus_drawings,
           }, context_instance=RequestContext(request))


def genus_redirect_view(request, genus_slug):
    return redirect('simplekey-genus', genus_slug=genus_slug)

def family_view(request, family_slug):
    family = get_object_or_404(Family, slug=family_slug.lower())
    family_images = family.images.filter(image_type__name='example image')
    family_drawings = family.images.filter(image_type__name='example drawing')
    return render_to_response('simplekey/family.html', {
           'item': family,
           'item_images': family_images,
           'item_drawings': family_drawings,
           }, context_instance=RequestContext(request))


def help_about(request):
    return render_to_response('simplekey/help_about.html', {
           'section_1_heading_blurb': get_blurb('section_1_heading'),
           'section_1_content_blurb': get_blurb('section_1_content'),
           'section_2_heading_blurb': get_blurb('section_2_heading'),
           'section_2_content_blurb': get_blurb('section_2_content'),
           'section_3_heading_blurb': get_blurb('section_3_heading'),
           'section_3_content_blurb': get_blurb('section_3_content'),
           }, context_instance=RequestContext(request))

def help_start(request):
    youtube_id = ''
    youtube_id_blurb = get_blurb('getting_started_youtube_id')
    if not youtube_id_blurb.startswith('[Provide text'):
        # We have an actual YouTube id defined in the database.
        youtube_id = youtube_id_blurb
    return render_to_response('simplekey/help_start.html', {
           'getting_started_blurb': get_blurb('getting_started'),
           'getting_started_youtube_id': youtube_id,
           }, context_instance=RequestContext(request))

def help_collections(request):
    return render_to_response('simplekey/help_collections.html', {
            'pages': Page.objects.order_by('number').all(),
            }, context_instance=RequestContext(request))

def help_glossary(request, letter):
    glossary = GlossaryTerm.objects.filter(visible=True).extra(
        select={'lower_term': 'lower(term)'}).order_by('lower_term')
    if letter == '1':
        # All terms whose names start with a number.
        glossary = glossary.filter(term__gte='1', term__lte='9z')
    else:
        glossary = glossary.filter(term__startswith=letter)
    # Case-insensitive sort
    return render_to_response('simplekey/help_glossary.html', {
            'this_letter': letter,
            'letters': '1' + string.ascii_lowercase,
            'glossary': glossary,
            }, context_instance=RequestContext(request))

def _get_pilegroup_youtube_id(pilegroup_name):
    pilegroup = PileGroup.objects.get(name=pilegroup_name)
    return pilegroup.youtube_id

def _get_pile_youtube_id(pile_name):
    pile = Pile.objects.get(name=pile_name)
    return pile.youtube_id
    
def _get_pilegroup_dict(pilegroup_name):
    return {'title': pilegroup_name, 
            'youtube_id': _get_pilegroup_youtube_id(pilegroup_name)}

def _get_pile_dict(pile_name):
    return {'title': pile_name, 'youtube_id': _get_pile_youtube_id(pile_name)}

def help_video(request):
    # The Getting Started video is first, followed by the pile
    # groups and piles in what is meant to be a reasonable
    # "collections order", i.e., each pile group in order it is
    # presented in the UI followed by the piles that belong to that group).
    videos = [{'title': 'Getting Started',
               'youtube_id': get_blurb('getting_started_youtube_id')}]
    videos.append(_get_pilegroup_dict('Ferns'))
    videos.append(_get_pile_dict('Equisetaceae'))
    videos.append(_get_pile_dict('Lycophytes'))
    videos.append(_get_pile_dict('Monilophytes'))
    videos.append(_get_pilegroup_dict('Woody Plants'))
    videos.append(_get_pile_dict('Woody Angiosperms'))
    videos.append(_get_pile_dict('Woody Gymnosperms'))
    videos.append(_get_pilegroup_dict('Aquatic Plants'))
    videos.append(_get_pile_dict('Non-Thalloid Aquatic'))
    videos.append(_get_pile_dict('Thalloid Aquatic'))
    videos.append(_get_pilegroup_dict('Graminoids'))
    videos.append(_get_pile_dict('Carex'))
    videos.append(_get_pile_dict('Poaceae'))
    videos.append(_get_pile_dict('Remaining Graminoids'))
    videos.append(_get_pilegroup_dict('Monocots'))
    videos.append(_get_pile_dict('Non-Orchid Monocots'))
    videos.append(_get_pile_dict('Orchid Monocots'))
    videos.append(_get_pilegroup_dict('Non-Monocots'))
    videos.append(_get_pile_dict('Composites'))
    videos.append(_get_pile_dict('Remaining Non-Monocots'))
    return render_to_response('simplekey/help_video.html', {
           'videos': videos,
           }, context_instance=RequestContext(request))

def video_pilegroup_view(request, pilegroup_slug):
    pilegroup = get_object_or_404(PileGroup, slug=pilegroup_slug)
    return render_to_response('simplekey/video.html', {
            'pilegroup': pilegroup,
            }, context_instance=RequestContext(request))

def video_pile_view(request, pilegroup_slug, pile_slug):
    pile = get_object_or_404(Pile, slug=pile_slug)
    if pile.pilegroup.slug != pilegroup_slug:
        raise Http404
    return render_to_response('simplekey/video.html', {
           'pilegroup': pile.pilegroup,
           'pile': pile,
           }, context_instance=RequestContext(request))
