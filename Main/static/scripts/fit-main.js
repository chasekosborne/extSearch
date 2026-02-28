/**
 * Fit game: URL load param and initial view/state.
 * Depends on: all other fit-*.js. Load last.
 */

/* Load submission from URL ?load=submission_id (from Explore Solutions "View in Fit") */
var loadedFromUrl = false;
(function checkLoadParam() {
  const params = new URLSearchParams(window.location.search);
  const loadId = params.get('load');
  if (loadId) {
    loadedFromUrl = true;
    loadSubmissionIntoBoard(loadId);
    const url = new URL(window.location.href);
    url.searchParams.delete('load');
    window.history.replaceState({}, '', url.pathname + (url.search || ''));
  }
})();

requestAnimationFrame(function() {
  if (!loadedFromUrl) centerViewOnGrid();
  updateSubmitButtonState();
  updateSquareDataDisplay();
});
