/**
 * API Configuration for Curling Dashboard
 * Auto-detects whether running on Pi (Flask) or Hostwinds (PHP)
 */

const API_CONFIG = {
    // Detect environment based on hostname
    isPHP: window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1',

    // API endpoints
    endpoints: {
        // Main dashboard data
        curlingData: function() {
            return this.isPHP ? '/api/curling_data.php' : '/curling_data.json';
        },

        // Health check
        health: function() {
            return this.isPHP ? '/api/health.php' : '/health';
        },

        // Coaching review
        coachGames: function() {
            return this.isPHP ? '/api/games.php' : '/coach_api/games';
        },
        coachShots: function() {
            return this.isPHP ? '/api/shots.php' : '/coach_api/shots';
        },

        // Bingo
        bingoCard: function() {
            return this.isPHP ? '/api/bingo_card.php' : '/bingo_api/card';
        },
        bingoCardById: function(id) {
            return this.isPHP ? `/api/bingo_card.php?id=${id}` : `/bingo_api/card/${id}`;
        },
        bingoOccurred: function() {
            return this.isPHP ? '/api/bingo_occurred.php' : '/bingo_api/occurred';
        },

        // Shot calling
        shotSuggest: function() {
            return this.isPHP ? '/api/shot_suggest.php' : '/shot_api/suggest';
        },
        shotAnalyze: function() {
            return this.isPHP ? '/api/shot_analyze.php' : '/shot_api/analyze';
        }
    },

    // Bind methods to have access to isPHP
    getEndpoint: function(name) {
        return this.endpoints[name].call(this);
    }
};

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = API_CONFIG;
}