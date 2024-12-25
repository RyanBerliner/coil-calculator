class LeverageCurve {
  HEIGHT = 200;
  MAX_LEVERAGE_MULTIPLIER = 0.2;  // ex: 0.2 is +/-20%

  constructor(node, config) {
    this._config = config;

    this._resolution = this._config.points.length;
    // TODO: move this assertion to the form initialization?
    console.assert(this._resolution >= 2, 'Must use a curve resolution of 2 or higher');

    this._node = node;
    this._canvas = this._node.querySelector('canvas');
    this._context = this._canvas.getContext('2d');

    // TODO: clean this up, should be dynamic on resize
    this._width = this._canvas.parentElement.parentElement.offsetWidth-40;
    this._canvas.height = this.HEIGHT;
    this._canvas.width = this._width;
    if (window.devicePixelRatio > 1) {
      this._canvas.width = this._width * window.devicePixelRatio;
      this._canvas.height = this.HEIGHT * window.devicePixelRatio;
      this._canvas.style.width = this._width + 'px';
      this._canvas.style.height = this.HEIGHT + 'px';
      this._context.scale(window.devicePixelRatio, window.devicePixelRatio);  
    }

    // interaction stuff
    this.interactionData = {
      x: 0,
      y: 0,
      prevY: null,
      currentX: null,
    };

    this._canvas.addEventListener('mousemove', this._moveCurveEvent.bind(this));
    this._canvas.addEventListener('touchmove', this._moveCurveEvent.bind(this));
    this._canvas.addEventListener('mousedown', this._startCurveEvent.bind(this), {capture: true});
    this._canvas.addEventListener('touchstart', this._startCurveEvent.bind(this), {capture: true});
    document.addEventListener('mouseup', this._endCurveEvent.bind(this));
    document.addEventListener('touchend', this._endCurveEvent.bind(this));

    this.draw();
  }

  get variables() {
    const { baseLeverage, travel, points } = this._config;
    const piecewiseRange = travel / 25.4 / (this._resolution-1);

    const travelLineFuncs = [];
    for (let i = 0; i < this._resolution-1; i++) {
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

  findRoot(k, w, r) {
    const { variables } = this;
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

  draw() {
    const { baseLeverage, points, travel } = this._config;
    const baseLeverageLabel = this._node.querySelector('[id="base-leverage"]');
    const upperLeverage = this._node.querySelector('[id="upper-leverage"]');
    const lowerLeverage = this._node.querySelector('[id="lower-leverage"]');

    baseLeverageLabel.innerHTML = baseLeverage.toFixed(1);
    upperLeverage.innerHTML = (baseLeverage + (baseLeverage * this.MAX_LEVERAGE_MULTIPLIER)).toFixed(1);
    lowerLeverage.innerHTML = (baseLeverage - (baseLeverage * this.MAX_LEVERAGE_MULTIPLIER)).toFixed(1);

    this._context.clearRect(0, 0, this._width, this.HEIGHT);
    // gridlines
    let num = 16;
    for (let i = 1; i < num; i++) {
      this._context.beginPath();
      this._context.lineWidth = 1;
      let color = '#f0f0f0';
      if (i % 4 == 0) {
        color = '#c5c5c5';
      }
      this._context.strokeStyle = color;
      this._context.moveTo(0, this.HEIGHT/num*i);
      this._context.lineTo(this._width, this.HEIGHT/num*i);
      this._context.stroke();
    }

    // the curve
    const curves = this._curveCubics();
    const segmentWidth = this._width/(this._resolution-1);
    this._context.beginPath();
    this._context.lineWidth = 3.5;
    this._context.strokeStyle = '#000';
    this._context.moveTo(0, this._getY(points[0]));
    let lastmod = 0;
    for (let i = 1; i < this._width; i++) {
      const index = Math.floor(i/segmentWidth);
      const mod = i%segmentWidth;
      // cannot use === 0 because of precision issues
      if (mod < lastmod || i === this._width) { 
        this._context.lineTo(i, this._getY(points[index]));
        lastmod = mod;
        continue;
      }
      lastmod = mod;
      this._context.lineTo(i, this._getY(curves[index](mod/segmentWidth)));
    }
    this._context.stroke();
  }

  _getY(y) {
    // this should return the Y coordinate in the canvas given a "Y" values
    // straight form the "points"
    //
    // 0 is the top (1 * max multiplier)
    // 1/2*(canvas height) is the middle 
    // (canvas height) is the bottom (0)
    const { baseLeverage } = this._config;
    const oldLower = 1 - (1*this.MAX_LEVERAGE_MULTIPLIER);
    const oldUpper = 1 + (1*this.MAX_LEVERAGE_MULTIPLIER);
    const newUpper = 0;
    const newLower = this.HEIGHT;
    return (y - oldLower)/(this.MAX_LEVERAGE_MULTIPLIER*2)*(-this.HEIGHT)+this.HEIGHT;
  }

  _updatePoint(idx, diff) {
    const newPoints = this._config.points.slice();
    newPoints[idx] += diff;

    const targetArea = this._resolution-1; // the target area of our inverse

    let area = 0;
    for (let i = 0; i < this._resolution-1; i++) {
      const x0 = i;
      const x1 = i+1;
      const y0 = newPoints[i];
      const y1 = newPoints[i+1];
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

    const perPointDiff = (targetArea-area)/(this._resolution-1);

    for (let i = 0; i < this._resolution-1; i++) {
      const x0 = i;
      const x1 = i+1;
      const y0 = newPoints[i];
      const y1 = newPoints[i+1];
      const m = (y1-y0)/(x1-x0);
      const b = y0-(m*x0);
      const q = x0;
      const p = x1;

      const recip = x => (1/(m*x+b))+perPointDiff;
      newPoints[i] = 1/recip(q);
      if ((i+1) === (newPoints.length-1)) {
        const end = recip(p);
        newPoints[i+1] = 1/recip(p);
      }
    }

    // Stay withing chart bounds
    if (Math.min(...newPoints) < 1-this.MAX_LEVERAGE_MULTIPLIER || Math.max(...newPoints) > 1+this.MAX_LEVERAGE_MULTIPLIER) {
      this._config.points.forEach((p, i) => {
        newPoints[i] = p;
      });
    }

    this._config.points = newPoints;
  }

  _curveCubics() {
    // i think this is how i want to smooth the curve
    // https://en.wikipedia.org/wiki/Cubic_Hermite_spline

    // use finite difference to calculate the slopes at each point
    let slopes = [];
    const points = this._config.points;
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


  _moveCurveEvent(event) {
    event.preventDefault();
    const { left, top } = this._canvas.getBoundingClientRect();
    this.interactionData.y = event.targetTouches ? event.targetTouches[0].clientY : event.clientY;
    this.interactionData.y -= top;
    this.interactionData.x = event.targetTouches ? event.targetTouches[0].clientX : event.clientX;
    this.interactionData.x -= left;
    if (this.interactionData.prevY == null) return;
    const { baseLeverage } = this._config;
    const range = baseLeverage * this.MAX_LEVERAGE_MULTIPLIER;
    const scale = this.HEIGHT / range;
    this._updatePoint(this.interactionData.currentX, (this.interactionData.prevY-this.interactionData.y)/scale);
    this.interactionData.prevY = this.interactionData.y;
  }


  _startCurveEvent(event) {
    event.preventDefault();
    const { left, top } = this._canvas.getBoundingClientRect();
    this.interactionData.prevY = event.targetTouches ? event.targetTouches[0].clientY : event.clientY;
    this.interactionData.prevY -= top;
    this.interactionData.x = event.targetTouches ? event.targetTouches[0].clientX : event.clientX;
    this.interactionData.x -= left;
    const i = Math.round(this.interactionData.x/(this._width/(this._resolution-1)));
    if (i >= 0 && i < this._resolution) this.interactionData.currentX = i;
  }

  _endCurveEvent(event) {
    this.interactionData.prevY = null;
  }
}
