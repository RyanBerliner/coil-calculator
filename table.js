const tableWrapper = document.body.querySelector('.table');
const cwLabel = tableWrapper.querySelector('.cw-label');
const cw = tableWrapper.querySelector('.cw');
const rwLabel = tableWrapper.querySelector('.rw-label');
const rw = tableWrapper.querySelector('.rw');

const tableStickyWrapper = document.body.querySelector('.table-sticky');
const stickyHeader = tableStickyWrapper.querySelector('.sticky-header');

let raf;
let initialized = false;

function updatePositioning() {
  window.cancelAnimationFrame(raf);
  raf = window.requestAnimationFrame(_updatePositioning);
}

function _updatePositioning() {
  if (!initialized) {
    return;
  }

  const { top, left, width } = tableWrapper.getBoundingClientRect();
  stickyHeader.style.left = left;
  stickyHeader.style.width = width;

  const cwLabelBounding = cwLabel.getBoundingClientRect();
  stickyHeader.querySelector('.cw-label').style.height = cwLabelBounding.height;
  stickyHeader.querySelector('.cw-label').style.width = cwLabelBounding.width;
  stickyHeader.querySelector('.cw-label').style.left = cwLabelBounding.left - left;

  const cwBounding = cw.getBoundingClientRect();
  stickyHeader.querySelector('.cw').style.height = cwBounding.height;
  stickyHeader.querySelector('.cw').style.width = cwBounding.width;
  stickyHeader.querySelector('.cw').style.left = cwBounding.left - left;

  if (top >= 0) {
    stickyHeader.classList.remove('show');
    return;
  }

  stickyHeader.classList.add('show');
}

window.addEventListener('resize', updatePositioning);
window.addEventListener('scroll', updatePositioning);

window.addEventListener('load', function() {
  const clonedCwLabel = cwLabel.cloneNode(true);
  const clonedCw = cw.cloneNode(true);
  stickyHeader.appendChild(clonedCwLabel);
  stickyHeader.appendChild(clonedCw);
  initialized = true;
  updatePositioning();
});

