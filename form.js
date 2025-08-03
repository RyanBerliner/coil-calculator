class ConfigurationForm {
  CURVE_DEFAULTS = {
    'mp': [1.1910723337537936, 1.0773217086778086, 0.9972675538606662, 0.958355556392723, 0.9362556697090503, 0.9250055500940926],
    'p': [1.0844669992350506, 1.0390499921419998, 1.0045834639152817, 0.9799678062000062, 0.9647754036058769, 0.9527764333429207],
    'flat': [1, 1, 1, 1, 1, 1],
    'd': [0.9318387626233346, 0.9710060185042217, 0.9980189840451251, 1.0189293258402035, 1.0318214303326663, 1.0383629141910782],
    'md': [0.8173567710047909, 0.9273342628257761, 1.001647761701074, 1.058240839433114, 1.0881483627896738, 1.1053960687852464],
  }

  constructor(form) {
    this.callbackResults = {};
    this._form = form;
    this._changeCallbacks = [];
    this._form.addEventListener('change', event => this._runChangeCallbacks(event));
    this._form.addEventListener('input', event => this._runChangeCallbacks(event));
    this._form.addEventListener('submit', event => {
      event.preventDefault();
      this._runChangeCallbacks(event);
    });

    const initPoints = this.CURVE_DEFAULTS[this._form.querySelector('select').value];
    if (initPoints) this.points = initPoints;
  }

  get stroke() { return parseInt(this.input('stroke').value) || 1; }
  get travel() { return parseInt(this.input('travel').value) || 0; }
  get riderWeight() { return parseInt(this.input('rider-weight').value) || 0; }
  get springWeight() { return parseInt(this.input('spring-weight').value) || 0; }
  get baseLeverage() { return this.travel/this.stroke; }
  get rearTireBias() {
    const value = parseInt(this.input('rear-bias').value) || 0;
    if (value <= 0) return 1/100;
    if (value >= 99) return 99/100;
    return value/100;
  }
  get normWeight() { return this.riderWeight*this.rearTireBias; }
  get points() {
    return this._pointsInputs.map(el => parseFloat(el.value));
  }

  set points(arrPoints) {
    const inputs = this._pointsInputs;
    arrPoints.forEach((val, idx) => inputs[idx].value = val);
    // console.log(JSON.stringify(arrPoints.map(p => p*this.baseLeverage)));
    // console.log('COPY', JSON.stringify(arrPoints));
    // TODO: probably need to manually call the change inputs?
    this._runChangeCallbacks();
  }

  addChangeCallback(callback, opts) {
    opts = opts ? opts : {};

    if (!opts.priority) {
      opts.priority = 0;
    }

    this._changeCallbacks.push([callback, opts]);

    this._changeCallbacks.sort((a, b) => {
      return a[1].priority - b[1].priority;
    });

    if (opts?.runInitial) {
      const result = callback();

      if (opts.dataKey) {
        this.callbackResults[opts.dataKey] = result;
      }

      this._runChangeCallbacks();
    }
  }

  input(name) {
    return this._form.querySelector(`[name="${name}"]`);
  }

  get _pointsInputs() {
    return Array.from(
      this._form.querySelector('[id="leverage-points"]').querySelectorAll('input')
    );
  }

  _runChangeCallbacks(event) {
    if (event?.target?.nodeName === 'SELECT') {
      const points = this.CURVE_DEFAULTS[event.target.value];
      if (points) this.points = points;
    } else {
      this._changeCallbacks.forEach(([callback, opts]) => {
        const result = callback(this);
        if (opts?.dataKey) {
          this.callbackResults[opts.dataKey] = result;
        }
      });
    }
  }
}
