define([
    'args',
    'simplekey/App3',
    'simplekey/Filter',
    'simplekey/FilterController',
    'simplekey/resources'
], function(args, App3, _Filter, _FilterController, resources) {

    var pile_slug = args.pile_slug;

    // Dojo code needs globals, so we create some.
    global_speciessectionhelper = null;
    Filter = _Filter;
    FilterController = _FilterController;

    App3.taxa = Ember.Object.create({
        len: 'Loading',   // placeholder until we have an integer to display
        show_list: false  // whether to show list or grid
    });

    App3.image_types = Ember.ArrayProxy.create({
        content: []
    });

    App3.TaxaView = Ember.View.extend({
        show_listBinding: 'App3.taxa.show_list',
        taxa_countBinding: 'App3.taxa.len',

        switch_photo_list: function(event) {
            // Tell the old Dojo species section helper to switch views.
            if (global_speciessectionhelper)
                global_speciessectionhelper.toggle_view(event);
        }
    });

    /* The FilterController can be activated once we know the full list
       of species that it will be filtering. */

    var async_key_vector = resources.key_vector('simple');
    var async_pile_taxa = resources.pile_species(pile_slug);

    $.when(async_key_vector, async_pile_taxa).done(function(kv, taxadata) {
        var simple_key_taxa = kv[0].species;
        var taxadata = _.filter(taxadata, function(taxon) {
            return _.indexOf(simple_key_taxa, taxon.id) != -1;
        });
        App3.set('taxadata', taxadata);  // TODO: put this somewhere else?

        var fc = FilterController.create({taxadata: taxadata});
        App3.set('filter_controller', fc);
        App3.set('family_filter', fc.filtermap.family);
        App3.set('genus_filter', fc.filtermap.genus);

        // Hide the "Loading..." spinner.
        $('.loading').hide();
    });

    /* The Family and Genus filters are Ember-powered <select> elements
       that the following logic keeps updated at all times with the set
       of legal family and genus values. */

    var choices_that_leave_more_than_zero_taxa = function(filter) {
        var other_taxa = App3.filter_controller.compute(filter);
        var keepers = _.filter(filter.values, function(value) {
            return _.intersect(value.taxa, other_taxa).length;
        });
        var choices = _.pluck(keepers, 'choice');
        choices.sort();
        choices.splice(0, 0, '');  // to "not select" a family or genus
        return choices;
    };

    App3.reopen({
        family_choices: function() {
            return choices_that_leave_more_than_zero_taxa(App3.family_filter);
        }.property('filter_controller.@each.value'),

        genus_choices: function() {
            return choices_that_leave_more_than_zero_taxa(App3.genus_filter);
        }.property('filter_controller.@each.value')
    });

    $('#family_clear').live('click', function(event) {
        App3.family_filter.set('value', '');
    });
    $('#genus_clear').live('click', function(event) {
        App3.genus_filter.set('value', '');
    });

    /* Other filters appear along the left sidebar, mediated through
       this convenient FilterView. */

    App3.FilterView = Ember.View.extend({
        answered: function() {
            // Return whether to assign the "answered" CSS class.
            return !! this.filter.value;
        }.property('filter.value'),

        show: function() {
            return this.filter.slug != 'family' && this.filter.slug != 'genus';
        }.property('filter.slug'),

        clear: function(event) {
            if (helper.filter_section.working_area)
                helper.filter_section.working_area.dismiss();
            this.filter.set('value', null);
        },

        work: function(event) {
            if ($(event.target).hasClass('clear-filter'))
                return;

            var filter = this.filter;
            var $target = $(event.target).closest('li');

            $('.option-list li').removeClass('active');
            $target.addClass('active');

            var y = $target.offset().top - 15;
            var async = resources.character_vector(this.filter.slug);
            $.when(async_pile_taxa, async).done(function(pile_taxa, values) {
                var ids = _.pluck(pile_taxa, 'id');
                filter.install_values({pile_taxa: ids, values: values});
                helper.filter_section.show_filter_working_onload(filter, y);
            });
        }
    });

    /* Filters need to be loaded. */

    // TODO: John, this is where the hash stuff goes back in, this time
    // without being Dojo-powered!

    var use_hash = false;
    if (use_hash) {
        resources.pile_characters(pile_slug).done(function(info) {
            // John, do awesome stuff here. :)
        });
    } else {
        resources.pile(pile_slug).done(function(pile_info) {
            _.each(pile_info.default_filters, function(filter_info) {
                App3.filter_controller.add(Filter.create({
                    slug: filter_info.short_name,
                    value_type: filter_info.value_type,
                    info: filter_info
                }));
                // Go ahead and start an async fetch, to make things
                // faster in case the user clicks on the filter.
                resources.character_vector(filter_info.short_name);
            });
        });
    }

    //

    require([
        'simplekey/results_overlay',
        'simplekey/results_photo_menu'
    ]);

    require([
        'jquery.tools.min',
        'order!jscrollpane'   // sk/results.js
    ], function() {
        require([
            'order!dojo_config',
            'order!/static/js/dojo/dojo.js',
            'order!/static/js/layers/nls/sk_en-us.js',
            'order!/static/js/layers/sk.js'
        ], function() {

            /* Glue: tell Dojo when the set of selected species
               changes. */

            App3.reopen({
                tell_dojo: function() {
                    var taxa = App3.filter_controller.taxa;
                    var t = _.filter(App3.taxadata, function(item) {
                        return _.indexOf(taxa, item.id) != -1;
                    });
                    t.sort(function(a, b) {
                        return a.scientific_name < b.scientific_name ? -1 : 1;
                    });
                    dojo.publish('/filters/query-result', [{species_list: t}]);
                }.observes('filter_controller.taxa')
            });

            require([
                'order!/static/gobotany/filters.js',
                'order!/static/gobotany/utils.js',
                'order!/static/gobotany/sk/glossary.js',
                'order!/static/gobotany/sk/photo.js',
                'order!/static/gobotany/sk/results.js',
                'order!/static/gobotany/sk/SpeciesSectionHelper.js',
                'order!/static/gobotany/sk/working_area.js',
                'order!/static/gobotany/sk/SearchSuggest.js'
            ], function() {
                require([
                    'order!simplekey/resources',   // now used in filters.js
                    'order!activate_search_suggest',
                    'order!activate_image_gallery',
                    'underscore-min',  // filters.js, etc
                    'sidebar',
                    'shadowbox',
                    'shadowbox_init'
                ], function() {
                    dojo.require('gobotany.sk.results');
                    dojo.addOnLoad(function() {
                        helper = gobotany.sk.results.ResultsHelper(args.pile_slug);
                    });
                });
            });
        });
    });
});
