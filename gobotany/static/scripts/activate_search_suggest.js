dojo.require('gobotany.sk.SearchSuggest');
dojo.addOnLoad(function() {
    var search_suggest = gobotany.sk.SearchSuggest('{{ query }}');
    search_suggest.setup();
});
