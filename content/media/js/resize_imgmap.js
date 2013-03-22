var resizeImgMaps = (function() {
  // Adapted from http://home.comcast.net/~urbanjost/semaphore.html
  function _map(lambda, list) {
    var newlist = [];
    for (var i = 0; i < list.length; i++) {
      var x = list[i];
      newlist.push(lambda.call(x));
    }
    return newlist;
  }
  
  function natural_width(img) {
    return img.naturalWidth ? img.naturalWidth : img.width;
  };
  function natural_height(img) {
    return img.naturalHeight ? img.naturalHeight : img.height;
  };
  function curr_width(img) {
    return img.width;
  };
  function curr_height(img) {
    return img.height;
  };
  
  function ResizableImgMap(img, map) {
    this.map = map;
    this.img = img;
  
    this._width = natural_width(this.img);
    this._height = natural_height(this.img);
  
    this._coords = [];
  
    var areas = this.map.children;
    for (var i = 0; i < areas.length; i++) {
      var area = areas[i];
      var coords = _map(function () { return Number(this); },
                        area.coords.split(','));
      this._coords.push([area, coords]);
    }
  }
  
  // Check image dimensions and resize the map appropriately
  ResizableImgMap.prototype.resize = function () {
    var cwidth = curr_width(this.img);
    var cheight = curr_height(this.img);
  
    var ratio = cwidth / this._width;
    if (!isFinite(ratio) || ratio == 0) {
      return;
    }
    _map(function () {
      var area = this[0];
      var coords = this[1];
      var scaled = _map(function () { return Math.round(this * ratio); },
                        coords);
      var coordstr = scaled.join(',');
      area.coords = coordstr;
    }, this._coords);
  };
  
  // Detect all images with maps; wrap and resize them.
  var ims = [];
  var imgs = document.getElementsByTagName('img');
  var img_maps = {};
  for (var i = 0; i < imgs.length; i++) {
    var img = imgs[i];
    if (img.useMap) {
      img_maps[img.useMap.slice(1)] = img;
    }
  }
  var maps = document.getElementsByTagName('map');
  for (var i = 0; i < maps.length; i++) {
    var map = maps[i];
    var img = img_maps[map.name];
  
    var im = new ResizableImgMap(img, map);
    ims.push(im);
  }
  function resizeImgMaps() {
    // Breathe for half a second so the style settles
    // FIXME Find a better way. Resize when detected image size change?
    setTimeout(function () {
      _map(function () { this.resize(); }, ims);
    }, 500);
  }
  return resizeImgMaps;
})();
