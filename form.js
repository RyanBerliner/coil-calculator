class ConfigurationForm {
  constructor(form) {
    this._form = form;
    this._changeCallbacks = [];
    this._form.addEventListener('change', () => this._runChangeCallbacks());
    this._form.addEventListener('submit', event => {
      event.preventDefault();
      this._runChangeCallbacks();
    });
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
    // TODO: probably need to manually call the change inputs?
    this._runChangeCallbacks();
  }

  addChangeCallback(callback) {
    this._changeCallbacks.push(callback);
  }

  input(name) {
    return this._form.querySelector(`[name="${name}"]`);
  }

  get _pointsInputs() {
    return Array.from(
      this._form.querySelector('[id="leverage-points"]').querySelectorAll('input')
    );
  }

  _runChangeCallbacks() {
    this._changeCallbacks.forEach(callback => callback(this));
  }
}
