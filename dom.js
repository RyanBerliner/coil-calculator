const config = new ConfigurationForm(document.querySelector('form'));
config.addChangeCallback(calculateCharacteristics);

const curveCanvas = document.querySelector('canvas#curve');
const curveHeight = 200;
const curveWidth = curveCanvas.parentElement.parentElement.offsetWidth-40-20;

const resolution = 6;
const maxLeverageMultiplier = 2;
const scale = curveHeight / maxLeverageMultiplier;
console.assert(resolution >= 2, 'Must use a curve resolution of 2 or higher');
const points = Array(resolution).fill(1);

let variables = getVariables();  // really need a better name for this
function getVariables() {
  const { baseLeverage, travel } = config;
  const piecewiseRange = travel / 25.4 / (resolution-1);

  const travelLineFuncs = [];
  for (let i = 0; i < points.length-1; i++) {
    const x0 = i*piecewiseRange;
    const x1 = (i+1)*piecewiseRange;
    const y0 = points[i]*baseLeverage;
    const y1 = points[i+1]*baseLeverage;
    const m = (y1-y0)/(x1-x0);
    const b = y0-(m*x0);
    travelLineFuncs.push({
      m,
      b,
      q: x0,
      p: x1, // consider setting to inf (or undefined) for last point?)
    });
  }

  let X = 0;
  let Y = 0;
  const strokeLineFuncs = travelLineFuncs.map(({m, b, q, p}) => {
    // the problem to solve is that if m === 0 this is undefined. need to find value as m approaches m
    let yValueAtPofIntegral = ((Math.log(m*p+b)-Math.log(m*q+b))/m)+Y;
    if (m === 0) {
      yValueAtPofIntegral = ((p-q)/(m*p+b))+Y;
    }
    const ret = {
      m,
      b,
      X,
      Y,
      q,
      p,
      // these are actually "stroke" q, p
      strokeq: Y,
      strokep: yValueAtPofIntegral,
    }
    Y = yValueAtPofIntegral;
    X = p;
    return ret;
  });

  return strokeLineFuncs;
}

function updatePoint(idx, diff) {
  const previousPoints = points.slice();
  points[idx] += diff;

  const targetArea = resolution-1; // the target area of our inverse

  let area = 0;
  for (let i = 0; i < points.length-1; i++) {
    const x0 = i;
    const x1 = i+1;
    const y0 = points[i];
    const y1 = points[i+1];
    const m = (y1-y0)/(x1-x0);
    const b = y0-(m*x0);
    const q = x0;
    const p = x1;
    // find the area under the inverse (the actual derivitive)
    if (m === 0) { // becuase of the problem if this is the case then b will not be 0 so OK
      area += (p-q)/b
    } else {
      area += (Math.log((m*p)+b)-Math.log((m*q)+b))/m
    }
  }

  const perPointDiff = (targetArea-area)/(resolution-1);

  for (let i = 0; i < points.length-1; i++) {
    const x0 = i;
    const x1 = i+1;
    const y0 = points[i];
    const y1 = points[i+1];
    const m = (y1-y0)/(x1-x0);
    const b = y0-(m*x0);
    const q = x0;
    const p = x1;

    const recip = x => (1/(m*x+b))+perPointDiff;
    points[i] = 1/recip(q);
    if ((i+1) === (points.length-1)) {
      const end = recip(p);
      points[i+1] = 1/recip(p);
    }
  }

  // Stay withing chart bounds
  if (Math.min(...points) < 0 || Math.max(...points) > 2) {
    previousPoints.forEach((p, i) => {
      points[i] = p;
    });
  }

  variables = getVariables();
  drawCurve();
  calculateCharacteristics();
}

function findRoot(variables, k, w, r) {
  for (let i = 0; i < variables.length; i++) {
    const {
      m,
      b,
      X,
      Y,
      strokeq,
      strokep,
    } = variables[i];

    function getVal(x) {
      let value = (m*x) - (m*Y) + Math.log((m*X)+b) - Math.log((k*x) / (w*r));
      return value;
    }

    function getDer(x) {
      return m-1/x;
    }

    let inspecting = strokeq || 1/Number.MAX_SAFE_INTEGER;  // prevent /0 error when getting dir
    let iteration = 0;
    let lastValue = undefined;
    const foundRoot = () => lastValue > -0.01 && lastValue < 0.01;
    // this is newtons method https://en.wikipedia.org/wiki/Newton's_method
    while (iteration < 1000 && !foundRoot()) {
      iteration++;
      lastValue = getVal(inspecting);
      const dir = getDer(inspecting);
      inspecting -= lastValue/dir;
    }

    if (foundRoot() && inspecting >= strokeq && inspecting < strokep) {
      return inspecting;
    }
  }

  return variables[variables.length-1].strokep;
}

// Animation stuff
const curveContext = curveCanvas.getContext('2d');

curveCanvas.height = curveHeight;
curveCanvas.width = curveWidth;

if (window.devicePixelRatio > 1) {
  curveCanvas.width = curveWidth * window.devicePixelRatio;
  curveCanvas.height = curveHeight * window.devicePixelRatio;
  curveCanvas.style.width = curveWidth + 'px';
  curveCanvas.style.height = curveHeight + 'px';
  curveContext.scale(window.devicePixelRatio, window.devicePixelRatio);  
}

function curveCubics() {
  // i think this is how i want to smooth the curve
  // https://en.wikipedia.org/wiki/Cubic_Hermite_spline

  // use finite difference to calculate the slopes at each point
  let slopes = [];
  for (let i = 0; i < points.length; i++) {
    // NOTE: that our points are uniformly spaces right now to all our runs are just set to 1 for simplicity
    let partials = [];
    if (i > 0) {
      partials.push((points[i]-points[i-1])/1);
    }
    if (i < points.length-1) {
      partials.push((points[i+1]-points[i])/1);
    }
    slopes[i] = (1/partials.length)*(partials.reduce((x,y) => x+y, 0));
  }
  let funcs = [];
  for (let i = 0; i < points.length-1; i++) {
    // this is when we need to interpolate
    const p0 = points[i], p1 = points[i+1], m0 = slopes[i], m1 = slopes[i+1];
    funcs.push(function inter(t) {
      return ((2*t**3 - 3*t**2 + 1)*p0) + ((t**3 - 2*t**2 + t)*m0) + ((-2*t**3 + 3*t**2)*p1) + ((t**3 - t**2)*m1);
    })
  }
  return funcs;
}

function getY(y) {
  return scale*(maxLeverageMultiplier) - (y*scale);
}

function drawCurve() {
  curveContext.clearRect(0, 0, curveWidth, curveHeight);
  // gridlines
  let num = 16;
  for (let i = 0; i <= num; i++) {
    curveContext.beginPath();
    curveContext.lineWidth = 1;
    let color = '#f0f0f0';
    if (i % 4 == 0) {
      color = '#c5c5c5';
    }
    curveContext.strokeStyle = color;
    curveContext.moveTo(0, curveHeight/num*i);
    curveContext.lineTo(curveWidth, curveHeight/num*i);
    curveContext.stroke();
  }

  // the curve
  const curves = curveCubics();
  const segmentWidth = curveWidth/(resolution-1);
  curveContext.beginPath();
  curveContext.lineWidth = 3.5;
  curveContext.strokeStyle = '#000';
  curveContext.moveTo(0, getY(points[0]));
  let lastmod = 0;
  for (let i = 1; i < curveWidth; i++) {
    const index = Math.floor(i/segmentWidth);
    const mod = i%segmentWidth;
    // cannot use === 0 because of precision issues
    if (mod < lastmod || i === curveWidth) { 
      curveContext.lineTo(i, getY(points[index]));
      lastmod = mod;
      continue;
    }
    lastmod = mod;
    curveContext.lineTo(i, getY(curves[index](mod/segmentWidth)));
  }
  curveContext.stroke();
}

drawCurve();

// canvas interaction
let x = 0, y = 0, prevY = null, currentX = null; 
function moveCurveEvent(event) {
  event.preventDefault();
  const { left, top } = curveCanvas.getBoundingClientRect();
  y = event.targetTouches ? event.targetTouches[0].clientY : event.clientY;
  y -= top;
  x = event.targetTouches ? event.targetTouches[0].clientX : event.clientX;
  x -= left;
  if (prevY == null) return;
  updatePoint(currentX, (prevY-y)/scale);
  prevY = y;
}
function startCurveEvent(event) {
  event.preventDefault();
  const { left, top } = curveCanvas.getBoundingClientRect();
  prevY = event.targetTouches ? event.targetTouches[0].clientY : event.clientY;
  prevY -= top;
  x = event.targetTouches ? event.targetTouches[0].clientX : event.clientX;
  x -= left;
  const i = Math.round(x/(curveWidth/(resolution-1)));
  if (i >= 0 && i < points.length) currentX = i;
}
function endCurveEvent(event) {
  prevY = null;
}
curveCanvas.addEventListener('mousemove', moveCurveEvent);
curveCanvas.addEventListener('touchmove', moveCurveEvent);
curveCanvas.addEventListener('mousedown', startCurveEvent, {capture: true});
curveCanvas.addEventListener('touchstart', startCurveEvent, {capture: true});
document.addEventListener('mouseup', endCurveEvent);
document.addEventListener('touchend', endCurveEvent);

const button = document.getElementById('simulate');
const baseLeverageLabel = document.getElementById('base-leverage');
const doubleLeverage = document.getElementById('double-leverage');
const wheelTravelLabel = document.getElementById('wheel-travel-label');

let sag;
let simulating = false;
let acc = 0;
let vel = 0;
let pos = 0;

button.addEventListener('mousedown', () => simulating = true);
button.addEventListener('touchstart', (event) => {
  event.preventDefault();
  simulating = true
});
button.addEventListener('mouseup', () => simulating = false);
button.addEventListener('touchend', () => {
  event.preventDefault();
  simulating = false;
});

function leverageOfShockAtStroke(s) {
  for (let i = 0; i < variables.length; i++) {
    const {strokeq, strokep, m, Y, X, b} = variables[i];
    if (s < strokep && s >= strokeq) {
      return Math.pow(Math.E, (m*s)-(m*Y)+Math.log((m*X)+b));
    }
  }
  // default to the "average" so it at least doesn't break
  return config.baseLeverage;
}

function calculateCharacteristics() {
  let { stroke, travel, baseLeverage, springWeight, riderWeight, rearTireBias } = config;
  baseLeverageLabel.innerHTML = baseLeverage.toFixed(1);
  doubleLeverage.innerHTML = (baseLeverage * 2).toFixed(1);
  wheelTravelLabel.innerHTML = travel.toFixed(0);

  variables = getVariables();

  // hooks law to solve for the spring rate
  // F = k*x
  // F   force
  // k   spring rate
  // x   deformation (sometimes called displacement)

  // This is what we need to swap out
  sag = findRoot(variables, springWeight, riderWeight, rearTireBias);

  sag *= 25.4 // mm
  sag /= stroke / 100 // %
  // Do a math.min incase our leverage curve estimate is a little off and would
  // lead to max sag at like 99.9 or 100.1 or something
  sag = Math.min(Math.round(sag * 100) / 100, 100).toFixed(2); // round to 2 decimals (so users can see something is changing
  document.getElementById('sag-output').innerHTML = sag;
}

calculateCharacteristics();

// the rest is the animation

const canvasNode = document.querySelector('canvas#animation');
const context = canvasNode.getContext('2d');
let cHeight;
let cWidth;
let baseTransform;

function setCanvas() {
  cHeight = window.outerHeight / 2;
  cWidth = canvasNode.parentElement.offsetWidth;
  canvasNode.height = cHeight;
  canvasNode.width = cWidth;

  if (window.devicePixelRatio > 1) {
    canvasNode.width = cWidth * window.devicePixelRatio;
    canvasNode.height = cHeight * window.devicePixelRatio;
    canvasNode.style.width = cWidth + 'px';
    canvasNode.style.height = cHeight + 'px';
    context.scale(window.devicePixelRatio, window.devicePixelRatio);  
  }

  baseTransform = context.getTransform();
}

setCanvas();

window.addEventListener('resize', () => {
  requestAnimationFrame(setCanvas);
});

function drawShock(stroke, compression, showSag) {
  // all in mm
  const originalCoilHeight = stroke * 2.33;
  const coilHeight = originalCoilHeight - compression;
  const coilThickness = 8;
  const coilWidth = 52;
  const coilCount = (stroke - (stroke % 12)) / 12;
  const shaftWidth = 13;
  const bumpStopWidthBottom = 29;
  const bumpStopWidthTop = 25;
  const bumpStopHeight = 22;
  const bumpStopSquish = 10;
  const trueShaftHeight = stroke + (bumpStopHeight - bumpStopSquish);
  const preloadWidth = 33;
  const plateThickness = coilThickness / 1.3;
  const bottomMountCenterHole = 20;
  const bottomMountWidth = 21;
  const mountRadius = 6;
  const topMountCenterHole = 17;
  const topMountRadius = 4;
  const bushingWidth = 2;
  const preloadHeight = stroke * 1.2;
  const pcBottomHeight = originalCoilHeight - trueShaftHeight - preloadHeight / 2;
  const coilBG = '#d46633';
  const coilFG = '#f07909';

  // we want to draw this in the center of the canvas and make as big as possible
  const shockHeight = originalCoilHeight + preloadHeight / 2;
  const scaleAmount = cHeight / (shockHeight + 200);  // extra num for padding top and bottom
  context.translate(cWidth / 2, cHeight / 2 + shockHeight / 2 * scaleAmount);
  context.scale(scaleAmount, scaleAmount);
  let middleTransform = context.getTransform();

  // the background coils
  context.translate(coilWidth / -2, -coilHeight);
  context.lineWidth = coilThickness;
  context.lineCap = 'round';
  context.beginPath();
  context.strokeStyle = coilBG;
  let coilGap = coilHeight / (coilCount + 0.5);
  for (let i = 0; i <= coilCount; i++) {
    let coilStartY = i * coilGap;
    let coilEndY = coilStartY + coilGap / 2;
    let deltaY = coilEndY - coilStartY;
    context.moveTo(0, coilStartY);
    const funcY = x => -0.5 * coilWidth * Math.cos(Math.PI * (1 / deltaY) * x);

    for (let x = 0; x <= deltaY; x += 1) {
      const y = funcY(x);
      context.lineTo(y + coilWidth / 2, coilStartY + x);
    }

    context.lineTo(coilWidth, coilStartY + deltaY);
    context.stroke();
  }
  context.setTransform(middleTransform);

  // draw the shaft in the middle
  context.translate(shaftWidth / -2, -trueShaftHeight);
  context.beginPath();
  context.fillStyle = 'lightgrey';
  context.fillRect(0, 0, shaftWidth, trueShaftHeight);
  context.setTransform(middleTransform);

  // bump stop
  context.fillStyle = 'black';
  context.translate(bumpStopWidthBottom / -2, -bumpStopHeight);
  context.beginPath();
  context.moveTo((bumpStopWidthBottom - bumpStopWidthTop) / 2, 0);
  context.lineTo((bumpStopWidthBottom - bumpStopWidthTop) / 2 + bumpStopWidthTop, 0);
  context.lineTo(bumpStopWidthBottom, bumpStopHeight);
  context.lineTo(0, bumpStopHeight);
  context.fill();
  context.setTransform(middleTransform);

  // top preload cylinder 
  context.translate(preloadWidth / -2, -coilHeight - preloadHeight / 2);
  context.lineWidth = 3;
  context.strokeStyle = 'black';
  context.beginPath();
  context.moveTo(0,0);
  for (let i = 0; i <= preloadHeight; i++) {
    context.moveTo(i % 6 === 0 ? -2 : 0, 1 * i);
    context.lineTo(preloadWidth + (i % 6 === 0 ? 2 : 0), 1 * i);
  }
  context.stroke();

  // top preload cylinder (bottom part)
  context.translate(0, preloadHeight);
  context.beginPath();
  context.moveTo(0, 0);
  context.lineTo(preloadWidth, 0);
  context.lineTo(preloadWidth, pcBottomHeight * 0.9);
  context.lineTo(preloadWidth * 0.9, pcBottomHeight);
  context.lineTo(preloadWidth * 0.1, pcBottomHeight);
  context.lineTo(0, pcBottomHeight * 0.9);
  context.lineTo(0, 0);
  context.fill();
  context.setTransform(middleTransform);

  const topOfMount = -topMountRadius - bushingWidth * 2;
  const mountWidth = (coilWidth * 3 + preloadWidth) / 4;
  const rounding = 3;

  context.translate(-mountWidth / 2, -coilHeight - preloadHeight / 2 - topMountCenterHole);
  context.beginPath();
  context.moveTo(0, 0);
  context.arcTo(mountWidth / 2 - topMountRadius - bushingWidth / 2, topOfMount, mountWidth / 2 + topMountRadius + bushingWidth / 2, topOfMount, rounding);
  context.arcTo(mountWidth / 2 + topMountRadius + bushingWidth / 2, topOfMount, mountWidth, 0, rounding);
  context.arcTo(mountWidth, 0, mountWidth, topMountCenterHole, rounding);
  context.arcTo(mountWidth, topMountCenterHole, 0, topMountCenterHole, rounding);
  context.arcTo(0, topMountCenterHole, 0, 0, rounding);
  context.arcTo(0, 0, mountWidth / 2 - topMountRadius - bushingWidth / 2, topOfMount, rounding);
  context.fill();

  context.beginPath();
  context.lineWidth = bushingWidth;
  context.strokeStyle = 'white';
  context.arc(mountWidth / 2, 0, topMountRadius, 2 * Math.PI, false);
  context.stroke();

  context.setTransform(middleTransform);

  // the foreground coils
  context.translate(coilWidth / -2, -coilHeight);
  context.beginPath();
  context.lineWidth = coilThickness;
  context.strokeStyle = coilFG;
  for (let i = 1; i <= coilCount; i++) {
    let coilStartY = i * coilGap;
    let coilEndY = coilStartY - coilGap / 2;
    let deltaY = coilEndY - coilStartY;
    context.moveTo(0, coilStartY);
    const funcY = x => -0.5 * coilWidth * Math.cos(Math.PI * (1 / deltaY) * x);

    for (let x = 0; x >= deltaY; x -= 1) {
      const y = funcY(x);
      context.lineTo(0 + y + coilWidth / 2, coilStartY + x);
    }

    context.lineTo(coilWidth, coilStartY + deltaY);
    context.stroke();
  }

  // the top edge
  context.beginPath();
  context.strokeStyle = coilFG;
  context.moveTo(0, 0);
  context.lineTo(coilWidth, 0);
  context.stroke();

  // draw the plate on the top
  context.translate(-coilThickness / 2, -plateThickness);
  context.beginPath();
  context.fillStyle = 'black';
  context.fillRect(0, 0, coilWidth + coilThickness, plateThickness);
  context.setTransform(middleTransform);

  // the bottom edge
  context.translate(-coilWidth / 2, 0);
  context.beginPath();
  context.moveTo(0, 0);
  context.lineTo(coilWidth, 0);
  context.stroke();


  // draw the plate on the bottom
  context.translate(-coilThickness / 2, 0);
  context.beginPath();
  context.fillStyle = 'black';
  context.fillRect(0, 0, coilWidth + coilThickness, plateThickness);
  context.setTransform(middleTransform);

  // bottom mount
  context.translate(bottomMountWidth / -2, 0);
  context.beginPath();
  context.fillStyle = 'black';

  context.moveTo(0,0);
  context.lineTo(bottomMountWidth, 0);
  const outerRadius = bottomMountWidth / 2;

  context.arcTo(bottomMountWidth, bottomMountCenterHole + outerRadius, 0, bottomMountCenterHole + outerRadius, outerRadius);
  context.arcTo(0, bottomMountCenterHole + outerRadius, 0, 0, outerRadius);

  context.moveTo(bottomMountWidth / 2, bottomMountCenterHole);
  context.arc(bottomMountWidth / 2, bottomMountCenterHole, mountRadius, 2 * Math.PI, false);

  context.fill('evenodd');
  context.setTransform(middleTransform);


  context.beginPath();
  context.strokeStyle = 'tan';
  context.lineWidth = bushingWidth;
  context.arc(0, bottomMountCenterHole, mountRadius, 2 * Math.PI, false);
  context.stroke();
  context.setTransform(middleTransform);

  if (showSag) {
    const w = 20;
    context.translate(coilWidth, -bumpStopHeight + bumpStopSquish);
    context.beginPath();
    context.fillStyle = 'black';
    context.strokeStyle = 'black';

    context.rect(0, -stroke, w, compression);
    context.stroke();
    context.fill();

    context.moveTo(w / 2, -stroke + compression);
    context.lineTo(w / 2, 0);
    context.moveTo(0, 0);
    context.lineTo(w, 0);
    context.stroke();
  }

  context.setTransform(baseTransform);
}

let last = 0;


function doPhysics(timestamp) {
  requestAnimationFrame(doPhysics);
  if (!last) {
    last = timestamp;
    return;
  }

  const { normWeight, springWeight, stroke } = config;
  const elapsed = (timestamp - last) / 1000; // sec
  last = timestamp;

  const forces = [];
  let springConstant = springWeight * 4.448; // N/in
  springConstant = springConstant / 25.4; // N/mm
  let weight = normWeight * leverageOfShockAtStroke(pos / 25.4) * 4.448; // N

  forces.push(simulating ? weight : 0);
  forces.push(-springConstant * pos);

  // we want to find the critical damping so it occilates a nice amount
  let criticalDamping = 2 * Math.sqrt(springConstant * weight) * elapsed; // https://en.wikipedia.org/wiki/Damping
  if (vel > 0) criticalDamping /= 3;  // compression damping third of rebound damping
  forces.push(-vel * criticalDamping);

  acc = forces.reduce((sum, x) => sum + x, 0);

  vel += acc * elapsed;
  if (vel > 0 && pos >= stroke) {
    vel = 0, pos = stroke;
  } else if (vel < 0 && pos <= 0) {
    vel = 0, pos = 0;
  } else {
    pos += vel * elapsed;
  }

  context.clearRect(0, 0, cWidth, cHeight);
  drawShock(stroke, pos, simulating);
}

requestAnimationFrame(doPhysics);
