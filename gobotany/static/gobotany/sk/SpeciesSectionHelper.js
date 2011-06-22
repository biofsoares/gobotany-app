/* This code should pass when run through Closure Linter
   (http://code.google.com/p/closure-linter/) and also JSLint
   (http://www.jslint.com/). For JSLint, we enable the option "Tolerate many
   var statements per function," and the globals declaration below. */
/*jslint vars: true, maxerr: 50, indent: 4 */
/*global window, document, clearTimeout, setTimeout, console, dojo, dijit,
  gobotany, global_setSidebarHeight, Shadowbox */

dojo.provide('gobotany.sk.SpeciesSectionHelper');

dojo.require('dojo.html');
dojo.require('dijit.Dialog');
dojo.require('dijit.form.Button');
dojo.require('gobotany.sk.plant_preview');

dojo.declare('gobotany.sk.SpeciesSectionHelper', null, {

    constructor: function(results_helper) {
        'use strict';
        // summary:
        //   Manages the species section of the results page
        // results_helper:
        //   An instance of gobotany.sk.results.ResultsHelper

        this.PHOTOS_VIEW = 'photos';
        this.LIST_VIEW = 'list';
        this.results_helper = results_helper;
        this.scroll_event_handle = null;
        this.current_view = this.PHOTOS_VIEW;
    },

    setup_section: function() {
        'use strict';

        // We need to perform a fresh species query whenever a filter
        // value changes anywhere on the page.
        dojo.subscribe('/sk/filter/change', this, 'perform_query');

        // Call the lazy image loader when the page loads.
        this.lazy_load_images();

        // Assign other events that will trigger the lazy image loader,
        // with timers so as not to suffer a quick succession of multiple
        // event firings.

        // No delay for scrolling allows images to load during the pressing
        // and holding of a cursor key.
        var SCROLL_WAIT_MS = 0;
        var scroll_timer;
        dojo.connect(window, 'onscroll', this, function() {
            clearTimeout(scroll_timer);
            scroll_timer = setTimeout(this.lazy_load_images, SCROLL_WAIT_MS);
        });

        var RESIZE_WAIT_MS = 500;
        var resize_timer;
        dojo.connect(window, 'onresize', this, function() {
            clearTimeout(resize_timer);
            resize_timer = setTimeout(this.lazy_load_images, RESIZE_WAIT_MS);
        });

        // Wire up tabs and a link for toggling between photo and list views.
        var tabs = dojo.query('#results-tabs a');
        var i;
        for (i = 0; i < tabs.length; i += 1) {
            dojo.connect(tabs[i], 'onclick', this, this.toggle_view);
        }

        var view_toggle_link = dojo.query('.list-all a')[0];
        dojo.connect(view_toggle_link, 'onclick', this, this.toggle_view);
    },

    perform_query: function() {
        'use strict';

        // Unbind the prior scroll event handler
        if (this.scroll_event_handle) {
            dojo.disconnect(this.scroll_event_handle);
        }

        var plant_list = dojo.query('#main .plant-list')[0];
        dojo.empty(plant_list);

        this.results_helper.filter_manager.perform_query({
            on_complete: dojo.hitch(this, 'on_complete_perform_query')
        });

        this.results_helper.save_filter_state();
    },

    on_complete_perform_query: function(data) {
        'use strict';

        // Update the species count everywhere it appears on the screen.
        dojo.query('.species-count').html(String(data.items.length));

        // Show the "Show" drop-down menu for image types, if necessary.
        if (this.current_view === this.PHOTOS_VIEW) {
            var show_menu = dojo.query('.show')[0];
            dojo.removeClass(show_menu, 'hidden');
        }

        // Display the results.
        var plant_list = dojo.query('#main .plant-list')[0];
        this.display_results(data.items, plant_list);

        // Show the "See a list" (or "See photos") link.
        var see_link = dojo.query('.list-all')[0];
        dojo.removeClass(see_link, 'hidden');

        global_setSidebarHeight();

        if (this.current_view === this.PHOTOS_VIEW) {
            // Signal the "Show:" button to scrape our data to discover what
            // kinds of thumbnail images are available.
            dojo.publish('results_loaded',
                         [{filter_manager: this.results_helper.filter_manager,
                           data: data}]);

            this.results_helper.species_section.lazy_load_images();
        }
    },

    default_image: function(species) {
        'use strict';

        var i;
        for (i = 0; i < species.images.length; i += 1) {
            var image = species.images[i];
            if (image.rank === 1 && image.type === 'habit') {
                return image;
            }
        }
        return {};
    },

    connect_plant_preview_popup: function(plant_link, species, pile_slug) {
        'use strict';

        dojo.connect(plant_link, 'onclick', species, function(event) {
            event.preventDefault();
            var plant = this;
            dijit.byId('plant-preview').show();
            gobotany.sk.plant_preview.show(
                plant,
                {'pile_slug': pile_slug});
        });
    },

    toggle_view: function(event) {
        'use strict';
    
        if (event.target.innerHTML.toLowerCase() === this.current_view) {
            // If the same tab as the current view was clicked, do nothing.
            return;
        }

        var HIDDEN_CLASS = 'hidden';
        var CURRENT_TAB_CLASS = 'current';
        var photos_tab = dojo.query('#results-tabs li:first-child a')[0];
        var list_tab = dojo.query('#results-tabs li:last-child a')[0];
        var view_type = dojo.query('.list-all a span.view-type')[0];
        var photos_show_menu = dojo.query('.show')[0];

        if (this.current_view === this.PHOTOS_VIEW) {
            this.current_view = this.LIST_VIEW;

            dojo.removeClass(photos_tab, CURRENT_TAB_CLASS);
            dojo.addClass(list_tab, CURRENT_TAB_CLASS);

            view_type.innerHTML = 'photos for';
            dojo.addClass(photos_show_menu, HIDDEN_CLASS);
        }
        else {
            this.current_view = this.PHOTOS_VIEW;

            dojo.removeClass(list_tab, CURRENT_TAB_CLASS);
            dojo.addClass(photos_tab, CURRENT_TAB_CLASS);

            view_type.innerHTML = 'a list of';
            dojo.removeClass(photos_show_menu, HIDDEN_CLASS);
        }

        this.perform_query();
    },

    get_number_of_rows_to_span: function(items, start) {
        /* From a starting point in a list of plant items, return the number
           of rows it takes to get to the next genus (or the end of the list).
         */
        'use strict';

        var rows = 1;
        var i;
        for (i = start; i < items.length; i += 1) {
            var is_last_item = (i === items.length - 1);
            if (is_last_item || items[i].genus !== items[i + 1].genus) {
                break;
            }
            else {
                rows += 1;
            }
        }

        return rows;
    },

    display_in_list_view: function(items, container) {
        /* Display plant results in a list view. Use a table, with hidden
           caption and header row for accessibility. */
        'use strict';

        var html =
            '<caption class="hidden">List of matching plants</caption>' +
            '<tr class="hidden"><th>Genus</th><th>Scientific Name</th>' +
            '<th>Common Name</th><th>Details</th></tr>';
        var i;
        for (i = 0; i < items.length; i += 1) {
            if (i > 0) {
                html += '<tr>';
            }
            else {
                html += '<tr class="first-visible">';
            }
            if (i === 0 || (items[i].genus !== items[i - 1].genus)) {
                var rowspan = this.get_number_of_rows_to_span(items, i);
                html += '<td class="genus" rowspan="' + String(rowspan) +
                    '">Genus: ' + items[i].genus + '</td>';
            }
            html += '<td class="scientific-name">';
            if (items[i].images[0] !== undefined) {
                html += '<a href="' + items[i].images[0].scaled_url +
                    '" title="Photo"><img ' +
                    'src="/static/images/icons/camera.jpg" alt=""></a>';
            }
            html += items[i].scientific_name + '</td>';
            html += '<td class="common-name">' + items[i].common_name +
                '</td>';
            html += '<td class="details"><a href="' +
                items[i].scientific_name.toLowerCase().replace(' ', '/') +
                '/">Details</a></td>';
            html += '</tr>';
        }

        var list = dojo.create('table', {'innerHTML': html});
        dojo.place(list, container);

        Shadowbox.setup('.plant-list table td.scientific-name a', 
                        {title: ''});
    },

    display_in_photos_view: function(items, container) {
        /* Display plant results as a grid of photo thumbnails with captions.
           Give plants in each genus a background color, cycling among several
           colors so plants in adjacent rows don't have the same color unless
           they are of the same genus. */
        'use strict';

        var SPECIES_PER_ROW = 4;
        var NUM_GENUS_COLORS = 5;
        var genus_color = 1;

        var num_rows = Math.ceil(items.length / SPECIES_PER_ROW);
        var r, row;
        for (r = 0; r < num_rows; r += 1) {
            var class_value = 'row';
            if (r === num_rows - 1) {
                class_value += ' last';
            }
            row = dojo.create('div', {'class': class_value});

            // Add the species for this row.
            var s;
            for (s = r * SPECIES_PER_ROW;
                 s < (r * SPECIES_PER_ROW) + SPECIES_PER_ROW; s += 1) {

                if (items[s] !== undefined) {
                    var species = items[s];
                    var plant_class_value = 'plant';
                    if (s === (r * SPECIES_PER_ROW)) {
                        plant_class_value += ' first';
                    }
                    else if ((s === (r * SPECIES_PER_ROW) +
                                     SPECIES_PER_ROW - 1) ||
                            (items[s + 1] === undefined)) {
                        plant_class_value += ' last';
                    }

                    // Set a background color, changing color if a new
                    // genus.
                    if (s > 0) {
                        if (items[s].genus !== items[s - 1].genus) {
                            genus_color += 1;
                            if (genus_color > NUM_GENUS_COLORS) {
                                genus_color = 1;
                            }
                        }
                    }
                    plant_class_value += ' genus' + String(genus_color);

                    var plant = dojo.create('div',
                        {'class': plant_class_value});
                    var path = window.location.pathname.split('#')[0];
                    var url = (path +
                        species.scientific_name.toLowerCase()
                            .replace(' ', '/') + '/');
                    var plant_link = dojo.create('a', {'href': url});
                    dojo.create('div', {'class': 'frame'}, plant_link);

                    var image_container = dojo.create('div',
                        {'class': 'img-container'});
                    var image = dojo.create('img', {'alt': ''});
                    dojo.attr(image, 'x-plant-id',
                              species.scientific_name);
                    var thumb_url = this.default_image(species).thumb_url;
                    if (thumb_url) { // undefined when no image available
                        // Set the image URL in a dummy attribute, so we can
                        // lazy-load images, switching to the proper attribute
                        // when the image comes into view.
                        dojo.attr(image, 'x-tmp-src', thumb_url);
                    }
                    dojo.place(image, image_container);
                    dojo.place(image_container, plant_link);

                    var name_html = '<span class="latin">' +
                        species.scientific_name + '</span>';
                    if (species.common_name) {
                        name_html += ' ' + species.common_name;
                    }
                    dojo.create('p', {'class': 'plant-name',
                        'innerHTML': name_html}, plant_link);

                    // Connect a "plant preview" popup. Pass species as
                    // context in the connect function, which becomes 'this'
                    // to pass along as the variable plant.
                    var pile_slug = this.results_helper.pile_slug;
                    this.connect_plant_preview_popup(plant_link, species,
                        pile_slug);

                    dojo.place(plant_link, plant);
                    dojo.place(plant, row);

                    if (plant_class_value.indexOf('last') > -1) {
                        dojo.create('div', {'class': 'clearit'}, row);
                    }
                }
            }
            dojo.place(row, container);
        }
    },

    display_results: function(items, plants_container) {
        'use strict';

        if (this.current_view === this.LIST_VIEW) {
            this.display_in_list_view(items, plants_container);
        }
        else {
            this.display_in_photos_view(items, plants_container);
        }
    },

    lazy_load_images: function() {
        'use strict';

        // If the current view is the List view, do nothing. This allows
        // event handlers for the photos view to remain in effect without
        // awkwardly removing and adding them when the user toggles views.
        //
        // Check the DOM instead of the SpeciesSectionHelper object, because
        // when this function is called via setTimeout, the 'this' context
        // is not what we need, and passing a saved reference to 'this', as
        // recommended for these situations, did not work.
        var list_view_table_nodes = dojo.query('.plant-list table');
        if (list_view_table_nodes.length > 0) {
            return;
        }

        var viewport = dijit.getViewport();
        var viewport_height = viewport.h;
        var scroll_top = 0;
        var scroll_left = 0;

        if (window.pageYOffset || window.pageXOffset) {
            scroll_top = window.pageYOffset;
            scroll_left = window.pageXOffset;
        }
        else if (document.documentElement &&
                 document.documentElement.scrollTop) {
            scroll_top = document.documentElement.scrollTop;
            scroll_left = document.documentElement.scrollLeft;
        }
        else if (document.body) {
            scroll_top = document.body.scrollTop;
            scroll_left = document.body.scrollLeft;
        }

        var image_elements = dojo.query('div.plant-list img');
        var i;
        for (i = 0; i < image_elements.length; i += 1) {
            var element = image_elements[i];
            if (element.style.visibility !== 'hidden' &&
                element.style.display !== 'none') {

                var current_element = element;
                var total_offset_left = current_element.offsetLeft;
                var total_offset_top = current_element.offsetTop;

                while (current_element.offsetParent !== null) {
                    current_element = current_element.offsetParent;
                    total_offset_left += current_element.offsetLeft;
                    total_offset_top += current_element.offsetTop;
                }

                var is_element_visible = false;
                // Only worry about top/bottom scroll visibility, not also
                // left/right scroll visibility.
                if (total_offset_top > (scroll_top - element.height) &&
                    total_offset_top < (viewport_height + scroll_top)) {

                    is_element_visible = true;
                }

                if (is_element_visible === true) {
                    var image_url = dojo.attr(element, 'x-tmp-src');

                    // Set the attribute that will make the image load.
                    dojo.attr(element, 'src', image_url);
                }
            }
        }
    }

});
