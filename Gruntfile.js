module.exports = function(grunt) {

    grunt.initConfig({
      nggettext_extract: {
        pot: {
          files: {
            'po/template.pot': ['teslarent/static/*.html']
          }
        },
      },

      nggettext_compile: {
        all: {
          files: {
            'teslarent/static/translations.js': ['po/*.po']
          }
         },
       },

    })

    grunt.loadNpmTasks('grunt-angular-gettext');

};
