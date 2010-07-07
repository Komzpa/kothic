#!/usr/bin/env python
# -*- coding: utf-8 -*-
#    This file is part of kothic, the realtime map renderer.

#   kothic is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.

#   kothic is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License
#   along with kothic.  If not, see <http://www.gnu.org/licenses/>.

#from debug import debug
from twms import projections
import psycopg2
import shapely.wkb

class Way:
  def __init__(self, tags, geom):

    self.cs = None
    #print [x.split("=") for x in tags.split(";")]
    self.tags = tags
    # calculating center point
    #c= geom
    #sumz = [(c[0],c[1])]
    #for k in range(2, len(c), 2):
    #  sumz.append((c[k], c[k + 1]))
    self.coords = geom
    #  left for the better times:
    self.center = reduce(lambda x, y: (x[0]+y[0],x[1]+y[1]), self.coords)
    self.center = (self.center[0]/len(self.coords),self.center[1]/len(self.coords))
    #debug(self.center)

class PostGisBackend:
  """
  A class that gives out vector data on demand.
  """
  

  def __init__(self,database = "dbname=gis user=mapz",max_zoom = 16,proj = "EPSG:3857", path = "tiles", lang = "ru", ):
    
    
 #   debug("Bakend created")
    self.database=database
    self.max_zoom = max_zoom            # no better tiles available
    self.path = path                    # path to tile files
    self.lang = lang                    # map language to use
    self.tiles = {}                     # loaded vector tiles go here
    self.proj = proj         # which projection used to cut map in tiles
    self.keep_tiles = 190                # a number of tiles to cache in memory
    self.tile_load_log = []             # used when selecting which tile to unload
    
  def get_vectors (self, bbox, zoom):
    a = psycopg2.connect(self.database)
    b = a.cursor()
    bbox = tuple(projections.from4326(bbox,self.proj))
    ### FIXME: hardcoded EPSG:3857 in database
    tables = ("planet_osm_line","planet_osm_polygon")  # FIXME: points
    resp = {}
    for table in tables:
      b.execute("SELECT * FROM %s WHERE way && SetSRID('BOX3D(%s %s,%s %s)'::box3d,900913);"%(table,bbox[0],bbox[1],bbox[2],bbox[3]))
      names = [q[0] for q in b.description]
      for row in b.fetchall():
        
          row_dict = dict(map(None,names,row))
          for k,v in row_dict.items():
            if not v:
              del row_dict[k]
          geom = shapely.wkb.loads(row_dict["way"].decode('hex'))
          ### FIXME: a dirty hack to basically support polygons, needs lots of rewrite
          try:
            geom = list(geom.coords)
          except NotImplementedError:
            "trying polygons"
            try:
              geom = geom.boundary
              geom = list(geom.coords)
              row_dict[":area"] = "yes"
            except NotImplementedError:
              "multipolygon"
              continue
              ### FIXME
          
          #geom = projections.to4326(geom, self.proj)
          del row_dict["way"]
          oid = row_dict["osm_id"]
          del row_dict["osm_id"]
          w = Way(row_dict, geom)
          #print row_dict
          resp[oid] = w
    return resp