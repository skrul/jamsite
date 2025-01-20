(function() {
  function Filter(filterRow) {
    this.init(filterRow);
  }
  Filter.prototype = {
    init: function(filterRow) {
      var that = this;
      var buttons = Array.from(filterRow.getElementsByClassName("filter"));
      that.activeFilters = new Set();
      buttons.forEach(function(button) {
        button.addEventListener(
          'click',
          function(e) {
            that.toggleFilter(e.target);
          },
          false
        );
      });
    },

    toggleFilter: function(filter) {
      var filterName = filter.id.replace("decade", "");
      var searchbar = document.getElementById("search");

      if (filter.classList.contains("button-primary")) {
        filter.classList.remove("button-primary");
        this.activeFilters.delete(filterName);
      } else {
        filter.classList.add("button-primary");
        this.activeFilters.add(filterName);
      }
      // trigger another search with filter updates
      searchbar.dispatchEvent(new Event('input'));
    },

    active: function() {
      return this.activeFilters;
    }
  }

  window.Filter = Filter;
})();
