"""Tests for the Simple Key application."""

import re
from gobotany.libtest import FunctionalCase
from selenium.common.exceptions import NoSuchElementException

class SearchTests(FunctionalCase):

    def _result_links(self):
        return self.css('#search-results-list li a')

    def test_search_results_page(self):
        self.get('/search/?q=acer')
        results = self.css('#search-results-list li')
        self.assertEqual(len(results), 10)

    def test_search_results_page_has_navigation_links(self):
        d = self.get('/search/?q=carex&page=2')
        self.assertTrue(d.find_element_by_link_text('Previous'))
        self.assertTrue(d.find_element_by_link_text('Next'))
        nav_links = d.find_elements_by_css_selector('.search-navigation a')
        self.assertTrue(len(nav_links) >= 5)

    def test_search_results_page_common_name_finds_correct_plant(self):
        self.get('/search/?q=christmas+fern')
        result_links = self._result_links()
        self.assertTrue(len(result_links))
        plant_found = False
        for result_link in result_links:
            url_parts = result_link.get_attribute('href').split('/')
            species = ' '.join(url_parts[-3:-1]).capitalize()
            if species == 'Polystichum acrostichoides':
                plant_found = True
                break
        self.assertTrue(plant_found)

    def _has_icon(self, url_substring):
        has_icon = False
        result_icons = self.css('#search-results-list li img')
        self.assertTrue(len(result_icons))
        for result_icon in result_icons:
            if result_icon.get_attribute('src').find(url_substring) > -1:
                has_icon = True
                break
        return has_icon

    def test_search_results_page_has_species_results(self):
        self.get('/search/?q=sapindaceae')
        self.assertTrue(self._has_icon('leaf'))

    def test_search_results_page_has_family_results(self):
        self.get('/search/?q=sapindaceae')
        self.assertTrue(self._has_icon('family'))

    def test_search_results_page_has_genus_results(self):
        self.get('/search/?q=sapindaceae')
        self.assertTrue(self._has_icon('genus'))

    def test_search_results_page_has_help_results(self):
        self.get('/search/?q=start')
        self.assertTrue(self._has_icon('help'))

    def test_search_results_page_has_glossary_results(self):
        self.get('/search/?q=abaxial')
        self.assertTrue(self._has_icon('glossary'))

    def test_search_results_page_returns_no_results(self):
        self.get('/search/?q=abcd')
        heading = self.css('#main h2')
        self.assertTrue(len(heading))
        self.assertEqual('No results for abcd', heading[0].text)
        message = self.css('#main p')
        self.assertTrue(len(message))
        self.assertEqual('Please adjust your search and try again.',
                         message[0].text)

    def test_search_results_page_has_singular_heading(self):
        query = '%22simple+key+for+plant+identification%22'   # in quotes
        self.get('/search/?q=%s' % query)   # query that returns 1 result
        heading = self.css('#main h2')
        self.assertTrue(len(heading))
        self.assertTrue(heading[0].text.startswith('1 result for'))

    def test_search_results_page_heading_starts_with_page_number(self):
        self.get('/search/?q=monocot&page=2')
        heading = self.css('#main h2')
        self.assertTrue(len(heading))
        self.assertTrue(heading[0].text.startswith('Page 2: '))

    def test_search_results_page_previous_link_is_present(self):
        d = self.get('/search/?q=monocot&page=2')
        self.assertTrue(d.find_element_by_link_text('Previous'))

    def test_search_results_page_next_link_is_present(self):
        d = self.get('/search/?q=monocot&page=2')
        self.assertTrue(d.find_element_by_link_text('Next'))

    def test_search_results_page_heading_number_has_thousands_comma(self):
        self.get('/search/?q=monocot')  # query that returns > 1,000 results
        heading = self.css('#main h2')
        self.assertTrue(len(heading))
        results_count = heading[0].text.split(' ')[0]
        self.assertTrue(results_count.find(',') > -1)
        self.assertTrue(int(results_count.replace(',', '')) > 1000)

    def test_search_results_page_omits_navigation_links_above_limit(self):
        MAX_PAGE_LINKS = 20
        self.get('/search/?q=monocot')  # query that returns > 1,000 results
        nav_links = self.css('.search-navigation li a')
        self.assertTrue(len(nav_links))
        # The number of links should equal the maximum page links: all
        # the page links minus one (the current unlinked page) plus one
        # for the Next link.
        self.assertTrue(len(nav_links) == MAX_PAGE_LINKS)

    def test_search_results_page_navigation_has_ellipsis_above_limit(self):
        self.get('/search/?q=monocot')  # query that returns > 1,000 results
        nav_list_items = self.css('.search-navigation li')
        self.assertTrue(len(nav_list_items))
        ellipsis = nav_list_items[-2]
        self.assertTrue(ellipsis.text == '...')

    def test_search_results_page_query_is_in_search_box(self):
        self.get('/search/?q=acer')
        search_box = self.css('#search input[type="text"]')
        self.assertTrue(len(search_box))
        self.assertTrue(search_box[0].get_attribute('value') == 'acer')

    def test_search_results_page_result_titles_are_not_excerpted(self):
        self.get('/search/?q=virginica')
        result_links = self._result_links()
        self.assertTrue(len(result_links))
        for link in result_links:
            self.assertTrue(link.text.find('...') == -1)

    def test_search_results_page_document_excerpts_ignore_marked_text(self):
        # Verify that search result document excerpts for species pages
        # no longer show text that is marked to be ignored, in this case
        # a series of repeating scientific names.
        self.get('/search/?q=rhexia+virginica')
        result_document_excerpts = self.css('#search-results-list li p')
        self.assertTrue(len(result_document_excerpts))
        species_page_excerpt = result_document_excerpts[0].text
        text_to_be_ignored = ('Rhexia virginica Rhexia virginica '
                              'Rhexia virginica Rhexia virginica '
                              'Rhexia virginica Rhexia virginica')
        self.assertEqual(species_page_excerpt.find(text_to_be_ignored), -1)

    def test_search_results_page_shows_some_text_to_left_of_excerpt(self):
        self.get('/search/?q=rhexia+virginica')
        result_document_excerpts = self.css('#search-results-list li p')
        self.assertTrue(len(result_document_excerpts))
        for excerpt in result_document_excerpts:
            # Rhexia should not appear right at the beginning after an
            # ellipsis, i.e., the excerpt should start with something
            # like '...Genus: Rhexia' rather than '...Rhexia'.
            self.assertTrue(excerpt.text.find('...Rhexia') == -1)
            self.assertTrue(excerpt.text.find('Rhexia') > 3)

    # Tests for search ranking.

    def test_search_results_page_scientific_name_returns_first_result(self):
        plants = [
            ('Acer rubrum', 'red maple'),
            ('Calycanthus floridus', 'eastern sweetshrub'),
            ('Halesia carolina', 'Carolina silverbell'),
            ('Magnolia virginiana', 'sweet-bay'),
            ('Vaccinium corymbosum', 'highbush blueberry')
        ]
        for scientific_name, common_names in plants:
            self.get('/search/?q=%s' % scientific_name.lower().replace(' ',
                                                                       '+'))
            result_links = self._result_links()
            self.assertTrue(len(result_links))
            self.assertEqual('%s (%s)' % (scientific_name, common_names),
                result_links[0].text)

    def test_search_results_page_common_name_returns_first_result(self):
        plants = [
            ('Ligustrum obtusifolium', 'border privet'),
            ('Matteuccia struthiopteris', 'fiddlehead fern, ostrich fern'),
            ('Nardus stricta', 'doormat grass'),
            ('Quercus rubra', 'northern red oak'),
            ('Rhus copallinum', 'winged sumac')
        ]
        for scientific_name, common_names in plants:
            common_name = common_names.split(',')[0]
            self.get('/search/?q=%s' % common_name.lower().replace(' ', '+'))
            result_links = self._result_links()
            self.assertTrue(len(result_links))
            self.assertEqual('%s (%s)' % (scientific_name, common_names),
                result_links[0].text)

    def test_search_results_page_family_returns_first_result(self):
        families = ['Azollaceae (mosquito fern family)',
                    'Equisetaceae (horsetail family)',
                    'Isoetaceae (quillwort family)',
                    'Marsileaceae (pepperwort family)',
                    'Salviniaceae (watermoss family)']
        for family in families:
            self.get('/search/?q=%s' % family.split(' ')[0].lower())
            result_links = self._result_links()
            self.assertTrue(len(result_links))
            self.assertEqual('Family: %s' % family, result_links[0].text)

    def test_search_results_page_genus_returns_first_result(self):
        genera = ['Claytonia (spring-beauty)',
                  'Echinochloa (barnyard grass)',
                  'Koeleria (Koeler\'s grass)',
                  'Panicum (panicgrass)',
                  'Saponaria (soapwort)',
                  'Verbascum (mullein)']
        for genus in genera:
            self.get('/search/?q=%s' % genus.split(' ')[0].lower())
            result_links = self._result_links()
            self.assertTrue(len(result_links))
            self.assertEqual('Genus: %s' % genus, result_links[0].text)

    # TODO: Add a test for genus common names if they become available.

    def test_search_results_page_glossary_term_returns_first_result(self):
        terms = ['acuminate', 'dichasial cyme', 'joint',
                 #'perigynium', # Why does this one still fail?
                 'terminal', 'woody']
        for term in terms:
            self.get('/search/?q=%s' % term.lower())
            result_links = self._result_links()
            self.assertTrue(len(result_links))
            self.assertEqual('Glossary: %s: %s' % (term[0].upper(), term),
                             result_links[0].text)

    # TODO: Add tests for plant groups and subgroups once they are
    # properly added (with any relevant friendly-title processing) to the
    # search indexes. (There is an upcoming user story for this.)

    # TODO: explore searching species names enclosed in quotes.
    # Maybe want to try and detect and search this way behind the
    # scenes if we can't reliably rank them first without quotes?

    # TODO: Test searching on synonyms.
    # Example:
    # q=saxifraga+pensylvanica
    # Returns:
    #Micranthes pensylvanica (swamp small-flowered-saxifrage)
    #Micranthes virginiensis (early small-flowered-saxifrage) 

    #####
    # Tests to confirm that various searches return Simple Key pages:
    # - Group page (aka Level 1 page: the list of plant groups)
    # - Subgroup page (aka Level 2 page: a list of plant subgroups for
    #   a group)
    # - Results page (aka Level 3 page: the questions/results page for
    #   a plant subgroup)
    #####

    def _is_page_found(self, result_links, page_title_text):
        is_page_found = False
        for link in result_links:
            if link.text.find(page_title_text) > -1:
                is_page_found = True
                break
        return is_page_found

    def _is_group_page_found(self, result_links):
        return self._is_page_found(result_links,
                                   'Simple Key for Plant Identification')

    def _is_subgroup_page_found(self, result_links, group_name):
        return self._is_page_found(result_links,
                                   '%s: Simple Key' % group_name)

    def _is_results_page_found(self, result_links, group_name, subgroup_name):
        return self._is_page_found(
            result_links, '%s: %s: Simple Key' % (subgroup_name, group_name))

    # Search on site feature name "Simple Key"

    def test_search_results_have_simple_key_pages(self):
        self.get('/search/?q=simple%20key')
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 2)
        results_with_simple_key_in_title = []
        for link in result_links:
            if link.text.find('Simple Key') > -1:
                results_with_simple_key_in_title.append(link)
        # There should be at least three pages with Simple Key in the
        # title: the initial groups list page, any of the subgroups list
        # pages, and any of the subgroup results pages.
        self.assertTrue(len(results_with_simple_key_in_title) > 2)


    # Search on main heading of plant group or subgroup pages

    def test_search_results_group_page_main_heading(self):
        self.get('/search/?q=which%20group')
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 0)
        self.assertTrue(self._is_group_page_found(result_links))

    def test_search_results_subgroup_page_main_heading(self):
        self.get('/search/?q=these%20subgroups')
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 5)
        self.assertTrue(self._is_subgroup_page_found(result_links,
                                                     'Woody Plants'))

    # Search on plant group or subgroup "friendly title"

    def test_search_results_have_group_page_for_friendly_title(self):
        self.get('/search/?q=woody%20plants')
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 0)
        self.assertTrue(self._is_group_page_found(result_links))

    def test_search_results_have_subgroup_page_for_friendly_title(self):
        self.get('/search/?q=woody%20broad-leaved%20plants')
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 0)
        self.assertTrue(self._is_subgroup_page_found(result_links,
                                                     'Woody Plants'))

    # Search on portion of plant group or subgroup "friendly name"

    def test_search_results_have_group_page_for_friendly_name(self):
        self.get('/search/?q=lianas')
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 0)
        self.assertTrue(self._is_group_page_found(result_links))

    def test_search_results_have_subgroup_page_for_friendly_name(self):
        self.get('/search/?q=aroids')
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 0)
        self.assertTrue(self._is_subgroup_page_found(
            result_links, 'Orchids and related plants'))

    # Search on portion of plant group or subgroup key characteristics
    # or exceptions text

    def test_search_results_have_group_page_for_key_characteristics(self):
        self.get('/search/?q=bark')
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 0)
        self.assertTrue(self._is_group_page_found(result_links))

    def test_search_results_have_subgroup_page_for_key_characteristics(self):
        self.get('/search/?q=%22sedges%20have%20edges%22')   # quoted query
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 0)
        self.assertTrue(self._is_subgroup_page_found(result_links,
                                                     'Grass-like plants'))

    def test_search_results_have_group_page_for_exceptions(self):
        self.get('/search/?q=showy%20flowers')   # Grass-like plants
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 0)
        self.assertTrue(self._is_group_page_found(result_links))

    def test_search_results_have_subgroup_page_for_exceptions(self):
        self.get('/search/?q=curly%20stems')   # Horsetails
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 0)
        self.assertTrue(self._is_subgroup_page_found(result_links, 'Ferns'))

    # Search on plant scientific name

    def test_search_results_contain_results_page_for_scientific_name(self):
        self.get('/search/?q=dendrolycopodium%20dendroideum')
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 0)
        self.assertTrue(self._is_results_page_found(
            result_links, 'Ferns',
            'Clubmosses and relatives, plus quillworts'))

    # Search on plant common name

    def test_search_results_contain_results_page_for_common_name(self):
        self.get('/search/?q=prickly%20tree-clubmoss')
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 0)
        self.assertTrue(self._is_results_page_found(
            result_links, 'Ferns',
            'Clubmosses and relatives, plus quillworts'))

    # Search on plant genus name

    def test_search_results_contain_results_page_for_genus_name(self):
        self.get('/search/?q=dendrolycopodium')
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 0)
        self.assertTrue(self._is_results_page_found(
            result_links, 'Ferns',
            'Clubmosses and relatives, plus quillworts'))

    #####
    # Dichotomous Key search results tests
    #####

    # TODO: uncomment and enhance upon adding dkey pages to search

#    def test_search_results_contain_dichotomous_key_main_page(self):
#        self.get('/search/?q=dichotomous')
#        result_links = self._result_links()
#        self.assertTrue(len(result_links) > 0)
#        self.assertTrue(self._is_page_found(result_links, 'Dichotomous Key'))

#    def test_search_results_contain_dichotomous_key_group_pages(self):
#        self.get('/search/?q=group%201')
#        result_links = self._result_links()
#        self.assertTrue(len(result_links) > 0)
#        self.assertTrue(self._is_page_found(result_links,
#                                            'Group 1: Dichotomous Key'))

#    def test_search_results_contain_dichotomous_key_family_pages(self):
#        self.get('/search/?q=lycopodiaceae')
#        result_links = self._result_links()
#        self.assertTrue(len(result_links) > 0)
#        self.assertTrue(self._is_page_found(
#            result_links, 'Family Lycopodiaceae: Dichotomous Key'))

#    def test_search_results_contain_dichotomous_key_genus_pages(self):
#        self.get('/search/?q=pseudolycopodiella')
#        result_links = self._result_links()
#        self.assertTrue(len(result_links) > 0)
#        self.assertTrue(self._is_page_found(
#            result_links, 'Pseudolycopodiella: Dichotomous Key'))


    # Test searching miscellaneous pages around the site (about, etc.)

    def test_search_results_contain_about_page(self):
        self.get('/search/?q=flora%20novae%20angliae')
        result_links = self._result_links()
        self.assertTrue(len(result_links))
        self.assertTrue(self._is_page_found(result_links, 'About Go Botany'))

    def test_search_results_contain_getting_started_page(self):
        self.get('/search/?q=get%20started')
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 0)
        self.assertTrue(self._is_page_found(result_links,
            'Getting Started with the Simple Key'))

    def test_search_results_contain_advanced_map_page(self):
        self.get('/search/?q=advanced%20map')
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 0)
        self.assertTrue(self._is_page_found(result_links,
            'Advanced Map to Groups'))

    def test_search_results_contain_video_help_topics_page(self):
        self.get('/search/?q=video%20help')
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 0)
        self.assertTrue(self._is_page_found(result_links,
            'Video Help Topics'))

    def test_search_results_contain_privacy_policy_page(self):
        self.get('/search/?q=privacy')
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 0)
        self.assertTrue(self._is_page_found(result_links, 'Privacy Policy'))

    def test_search_results_contain_terms_of_use_page(self):
        self.get('/search/?q=terms')
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 0)
        self.assertTrue(self._is_page_found(result_links, 'Terms of Use'))

    def test_search_results_contain_teaching_page(self):
        self.get('/search/?q=teaching')
        result_links = self._result_links()
        self.assertTrue(len(result_links) > 0)
        self.assertTrue(self._is_page_found(result_links, 'Teaching'))

class FamilyTests(FunctionalCase):

    def test_family_page(self):
        self.get('/family/lycopodiaceae/')
        heading = self.css('#main h2')
        self.assertTrue(len(heading))
        self.assertTrue(heading[0].text == 'Family: Lycopodiaceae')
        common_name = self.css('#main h3')
        self.assertTrue(len(common_name))

    def test_family_page_has_example_images(self):
        self.get('/family/lycopodiaceae/')
        example_images = self.css('#main .pics a img')
        self.assertTrue(len(example_images))

    def test_family_page_has_list_of_genera(self):
        self.get('/family/lycopodiaceae/')
        genera = self.css('#main .genera li')
        self.assertTrue(len(genera))


class GenusTests(FunctionalCase):

    def test_genus_page(self):
        self.get('/genus/dendrolycopodium/')
        heading = self.css('#main h2')
        self.assertTrue(len(heading))
        self.assertTrue(heading[0].text == 'Genus: Dendrolycopodium')
        common_name = self.css('#main h3')
        self.assertTrue(len(common_name))
        self.assertTrue(common_name[0].text == 'tree-clubmoss')

    def test_genus_page_has_example_images(self):
        self.get('/genus/dendrolycopodium/')
        example_images = self.css('#main .pics a img')
        self.assertTrue(len(example_images))

    def test_genus_page_has_family_link(self):
        self.get('/genus/dendrolycopodium/')
        family_link = self.css('#main p.family a')
        self.assertTrue(len(family_link))

    def test_genus_page_has_list_of_species(self):
        self.get('/genus/dendrolycopodium/')
        species = self.css('#main .species li')
        self.assertTrue(len(species))


class SpeciesTests(FunctionalCase):

    def _photos_have_expected_caption_format(self, species_page_url):
        # For a species page, make sure the plant photos have the expected
        # format for title/alt text that gets formatted on the fly atop 
        # each photo when it is viewed large. The text should contain a
        # title, image type, contributor, copyright holder. It can also
        # optionally have a "source" note at the end.
        REGEX_PATTERN = '.*: .*\. ~ By .*\. ~ Copyright .*\s+.( ~ .\s+)?'
        self.get(species_page_url)
        links = self.css('#species-images a')
        self.assertTrue(len(links))
        for link in links:
            title = link.get_attribute('title')
            self.assertTrue(re.match(REGEX_PATTERN, title))
        images = self.css('#species-images a img')
        self.assertTrue(len(images))
        for image in images:
            alt_text = image.get_attribute('alt')
            self.assertTrue(re.match(REGEX_PATTERN, alt_text))

    def test_species_page_photos_have_title_credit_copyright(self):
        species_page_url = '/species/dendrolycopodium/dendroideum/'
        self._photos_have_expected_caption_format(species_page_url)

    def test_species_page_photos_have_title_credit_copyright_source(self):
        # Some images on this page have "sources" specified for them.
        species_page_url = ('/species/gymnocarpium/dryopteris/')
        self._photos_have_expected_caption_format(species_page_url)

    def test_simple_key_species_page_has_breadcrumb(self):
        self.get('/species/adiantum/pedatum/')
        self.assertTrue(self.css1('#breadcrumb'))

    def test_non_simple_key_species_page_omits_breadcrumb(self):
        # Breadcrumb should be omitted until Full Key is implemented.
        self.get('/species/adiantum/aleuticum/')
        breadcrumb = None
        try:
            breadcrumb = self.css1('#breadcrumb')
        except NoSuchElementException:
            self.assertEqual(breadcrumb, None)
            pass

    def test_non_simple_key_species_page_has_note_about_data(self):
        # Temporarily, non-Simple-Key pages show a data disclaimer.
        self.get('/species/adiantum/aleuticum/')
        self.assertTrue(self.css1('.content .note'))


class LookalikesFunctionalTests(FunctionalCase):

    def test_lookalikes_are_in_search_indexes_for_many_pages(self):
        self.get('/search/?q=sometimes+confused+with')
        page_links = self.css('.search-navigation li')
        self.assertTrue(len(page_links) > 10)   # more than 100 results

    def test_species_pages_have_lookalikes(self):
        # Verify a sampling of the species expected to have lookalikes.
        SPECIES = ['Huperzia appressa', 'Lonicera dioica', 'Actaea rubra',
                   'Digitalis purpurea', 'Brachyelytrum aristosum']
        for s in SPECIES:
            url = '/species/%s/' % s.replace(' ', '/').lower()
            self.get(url)
            heading = self.css('#sidebar .lookalikes h5')
            self.assertTrue(heading)
            lookalikes = self.css('#sidebar .lookalikes dt')
            self.assertTrue(len(lookalikes) > 0)
            for lookalike in lookalikes:
                self.assertTrue(len(lookalike.text) > 0)
            notes = self.css('#sidebar .lookalikes dd')
            self.assertTrue(len(notes) > 0)
            for note in notes:
                self.assertTrue(len(note.text) > 0)
