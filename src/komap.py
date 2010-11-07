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


from debug import debug, Timer
from mapcss import MapCSS
import sys
from libkomapnik import *

try:
        import psyco
        psyco.full()
except ImportError:
        pass

minzoom = 1
maxzoom = 19


style = MapCSS(minzoom, maxzoom)     #zoom levels
style.parse(open("styles/gisrussa.mapcss","r").read())

mapniksheet = {}

# {zoom: {z-index: [{sql:sql_hint, cond: mapnikfiltercondition, subject: subj, style: {a:b,c:d..}},{r2}...]...}...}


for zoom in range (minzoom, maxzoom):
  mapniksheet[zoom] = []#{}
  zsheet = mapniksheet[zoom]
  for chooser in style.choosers:
    if chooser.get_sql_hints(chooser.ruleChains[0][0].subject, zoom)[0]:
      styles = chooser.styles[0]
      # unfold foo, bar {...} -> foo {...} bar {...}
      for rc in chooser.ruleChains[0]:
        if rc.test_zoom(zoom):
          #zindex = styles.get("z-index",0)
          #if zindex not in zsheet:
          #  zsheet[zindex] = []
          chooser_entry = {}
          chooser_entry["sql"] = "("+ chooser.get_sql_hints(rc.subject,zoom)[1] +")"
          chooser_entry["style"] = styles
          chooser_entry["type"] = rc.subject.lower()
          #sys.stderr.write(str(rc))
          chooser_entry["rule"] = rc.conditions
          chooser_entry["chooser"] = chooser
          ## Unfold * -> node,line,area; way-> area,line
          if chooser_entry["type"] == "*":
            chooser_entry["type"] = "node"
            zsheet.append(chooser_entry.copy())
            chooser_entry["type"] = "way"
          if chooser_entry["type"] == "way":
            chooser_entry["type"] = "line"
            zsheet.append(chooser_entry.copy())
            chooser_entry["type"] = "area"
            zsheet.append(chooser_entry.copy())
            chooser_entry["type"] = "way"
          elif chooser_entry["type"] in ("area", "node", "line"):
            zsheet.append(chooser_entry.copy())
        

ms2 = {}

def rule_list_and (lst, tr):
  """
  and's list of rules with a rule tr
  returns new list or False if r&rules is always false.
  """
  if lst == False:
    return False
  r = lst[:]
  rap = False
  for tt in lst:
    #print tr, tt
    tp = tr.and_with(tt)
   # print tp
    if tp:
      if len(tp) == 1: # can be 1 or 2
        if tp[0] != tr and tp[0] != tt:
          r.remove(tr)
          r.remove(tt)
          r.append(tp[0])
          rap = True
        elif tp[0] == tr:
         # print r, tr
          r.remove(tt)
          #rap = True
        elif tp[0] == tt:
          rap = True
      
    else:
      return False
  if not rap:
    #print "bad", tr
    r.append(tr)
  return r


  
for zoom in range (minzoom, maxzoom):
  ms2[zoom] = []
  zsheet = ms2[zoom]
  zsheet.append(mapniksheet[zoom].pop(0))
  for chooser in mapniksheet[zoom]:
    zs2 = [] # where we add new things
    merged = False
    for c2 in zsheet:
      #print c2["type"] == chooser["type"]
      if c2["type"] == chooser["type"]:
        #print c2
        a = chooser["rule"]
        b = c2["rule"]
        #print a
        #print b
        
        ## Trying to merge two rules
        ## in result, we'll get three: a&b, a&!b, !a&b
        # a&b
        r = a[:]
        
        for ib in b:
          
          r = rule_list_and(r, ib)
          if not r:
            break
        else:
          ce = c2.copy()
          ce["rule"] = r
          #print "ab",r,a,b
          for prop in chooser["style"]:
            ce["style"][prop] = chooser["style"][prop]
          zs2.append(ce)
          merged = True
        # a&!b
        nb = [i.inverse() for i in b]
        for ib in nb:
          r = rule_list_and(a, ib)
          if r:
            ce = chooser.copy()
            ce["rule"] = r
            #print "a!b",r,a,nb
            zs2.append(ce)
            merged = True
        # !a&b
        na = [i.inverse() for i in a]
        for ia in na:
          r = rule_list_and(b, ia)
          if r:
            ce = c2.copy()
            ce["rule"] = r
            #print "!ab",r,na,b
            zs2.append(ce)
            merged = True
      if not merged:
        zs2.append(chooser)
      ms2[zoom] = zs2
      zsheet = ms2[zoom]
      
        


        
        #na = [i.inverse for i in c2["rule"]]
        #rs = []
        #for added in na:
          #if 
    #zsheet.append(chooser)

# calculate evals where possible

# drop useless properties

# split things into lines, polygons, texts, shields...

# merge back what's possible



mapniksheet = {}
for zoom in range (minzoom, maxzoom):
  mapniksheet[zoom] = {}
  zsheet = mapniksheet[zoom]
  for chooser in ms2[zoom]:
    zindex = float(chooser["style"].get("z-index",0))
    chooser["sql"] = "("+ " AND ".join([i.get_sql()[1] for i in chooser["rule"]]) +")"
    chooser["rule"] = [chooser["rule"]]
    if zindex not in zsheet:
      zsheet[zindex] = []
    zsheet[zindex].append(chooser)
   



#print mapniksheet

mfile = sys.stdout


mfile.write(xml_start(style.get_style("canvas", {}, maxzoom)[0].get("fill-color", "#ffffff")))
for zoom, zsheet in mapniksheet.iteritems():
  x_scale = xml_scaledenominator(zoom)
  ta = zsheet.keys()
  ta.sort(key=float)

  for zindex in ta:    
    ## areas pass
    sql = set()
    itags = set()
    xml = xml_style_start()
    for entry in zsheet[zindex]:
      if entry["type"] in ("way", "area", "polygon"):
        if "fill-color" in entry["style"] or "fill-image" in entry["style"]:
          xml += xml_rule_start()
          xml += x_scale
          rulestring = " or ".join([ "("+ " and ".join([i.get_mapnik_filter() for i in rule]) + ")" for rule in entry["rule"]])
          xml += xml_filter(rulestring)
          if "fill-color" in entry["style"]:
            xml += xml_polygonsymbolizer(entry["style"].get("fill-color", "black"), entry["style"].get("fill-opacity", "1"))
          if "fill-image" in entry["style"]:
            xml += xml_polygonpatternsymbolizer(entry["style"].get("fill-image", ""))
          sql.add(entry["sql"])
          itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
          xml += xml_rule_end()

          

    xml += xml_style_end()
    sql.discard("()")
    if sql:
      mfile.write(xml)
      sql = " OR ".join(sql)
      mfile.write(xml_layer("postgis", "polygon", itags, sql ))
    else:
      xml_nolayer()
  for layer_type, entry_types in [("polygon",("way","area")),("line",("way", "line"))]:
    for zlayer in range(-6,7):
      for zindex in ta:
        ## casings pass
        sql = set()
        itags = set()
        xml = xml_style_start()
        for entry in zsheet[zindex]:
          if entry["type"] in entry_types:
            if "-x-mapnik-layer" in entry["style"]:
              if zlayer != -6 and entry["style"]["-x-mapnik-layer"] == "bottom":
                continue
              if zlayer != 6 and entry["style"]["-x-mapnik-layer"] == "top":
                continue
            elif zlayer not in range(-5,6):
              continue
            if "casing-width" in entry["style"]:
              xml += xml_rule_start()
              xml += x_scale
              rulestring = " or ".join([ "("+ " and ".join([i.get_mapnik_filter() for i in rule]) + ")" for rule in entry["rule"]])
              xml += xml_filter(rulestring)
              xml += xml_linesymbolizer(color=entry["style"].get("casing-color", "black"),
                width=2*float(entry["style"].get("casing-width", 1))+float(entry["style"].get("width", 0)),
                opacity=entry["style"].get("casing-opacity", entry["style"].get("opacity","1")),
                linecap=entry["style"].get("casing-linecap", entry["style"].get("linecap","butt")),
                linejoin=entry["style"].get("casing-linejoin", entry["style"].get("linejoin", "round")),
                dashes=entry["style"].get("casing-dashes",entry["style"].get("dashes", "")))

              sql.add(entry["sql"])
              itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
              xml += xml_rule_end()

        xml += xml_style_end()
        sql.discard("()")
        if sql:
          mfile.write(xml)
          sql = " OR ".join(sql)
          if zlayer == 0:
            sql = "("+ sql +') and ("layer" not in ('+ ", ".join(['\'%s\''%i for i in range(-5,6) if i != 0])+") or \"layer\" is NULL)"
          elif zlayer <=5 and zlayer >= -5:
            sql = "("+ sql +') and "layer" = \'%s\''%zlayer
          mfile.write(xml_layer("postgis", layer_type, itags, sql ))
        else:
          xml_nolayer()

      for zindex in ta:
        ## lines pass
        sql = set()
        itags = set()
        xml = xml_style_start()
        for entry in zsheet[zindex]:
          if entry["type"] in entry_types:
            if "-x-mapnik-layer" in entry["style"]:
              if zlayer != -6 and entry["style"]["-x-mapnik-layer"] == "bottom":
                continue
              if zlayer != 6 and entry["style"]["-x-mapnik-layer"] == "top":
                continue
            elif zlayer not in range(-5,6):
              continue
            if "width" in entry["style"] or "line-style" in entry["style"]:
              xml += xml_rule_start()
              xml += x_scale
              rulestring = " or ".join([ "("+ " and ".join([i.get_mapnik_filter() for i in rule]) + ")" for rule in entry["rule"]])
              xml += xml_filter(rulestring)
              if "width" in entry["style"]:
                xml += xml_linesymbolizer(color=entry["style"].get("color", "black"),
                  width=entry["style"].get("width", "1"),
                  opacity=entry["style"].get("opacity", "1"),
                  linecap=entry["style"].get("linecap", "round"),
                  linejoin=entry["style"].get("linejoin", "round"),
                  dashes=entry["style"].get("dashes", ""))
              if "line-style" in entry["style"]:
                if entry["style"]["line-style"] == "arrows":
                  xml += xml_hardcoded_arrows()
                else:
                  xml += xml_linepatternsymbolizer(entry["style"]["line-style"])
              sql.add(entry["sql"])
              itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
              xml += xml_rule_end()

        xml += xml_style_end()
        sql.discard("()")
        if sql:
          mfile.write(xml)
          sql = " OR ".join(sql)
          if zlayer == 0:
            sql = "("+ sql +') and ("layer" not in ('+ ", ".join(['\'%s\''%i for i in range(-5,6) if i != 0])+") or \"layer\" is NULL)"
          elif zlayer <=5 and zlayer >= -5:
            sql = "("+ sql +') and "layer" = \'%s\''%zlayer
          mfile.write(xml_layer("postgis", layer_type, itags, sql ))
        else:
          xml_nolayer()
  for layer_type, entry_types in {"line":("way", "line"), "polygon":("way","area"), "point": ("node", "point")}.iteritems():
    for zindex in ta:
      ## icons pass
      sql = set()
      itags = set()
      xml = xml_style_start()
      for entry in zsheet[zindex]:
        if entry["type"] in entry_types:
          if "icon-image" in entry["style"]:
            xml += xml_rule_start()
            xml += x_scale
            rulestring = " or ".join([ "("+ " and ".join([i.get_mapnik_filter() for i in rule]) + ")" for rule in entry["rule"]])
            xml += xml_filter(rulestring)
            xml += xml_pointsymbolizer(
              path=entry["style"].get("icon-image", ""),
              width=entry["style"].get("icon-width", ""),
              height=entry["style"].get("icon-height", ""),
              
              opacity=entry["style"].get("opacity", "1"))

            sql.add(entry["sql"])
            itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
            xml += xml_rule_end()

      xml += xml_style_end()
      sql.discard("()")
      if sql:
        mfile.write(xml)
        sql = " OR ".join(sql)
        mfile.write(xml_layer("postgis", layer_type, itags, sql ))
      else:
        xml_nolayer()
  for layer_type, entry_types in {"line":("way", "line"), "polygon":("way","area"), "point": ("node", "point")}.iteritems():
    for zindex in ta:
      ## text pass
      sql = set()
      itags = set()
      ttext = ""
      xml = xml_style_start()
      for entry in zsheet[zindex]:
        if entry["type"] in entry_types:#, "node", "line", "point"):
          if "text" in entry["style"]:
            ttext = entry["style"]["text"].extract_tags().pop()
            tface = entry["style"].get("font-family","DejaVu Sans Book")
            tsize = entry["style"].get("font-size","10")
            tcolor = entry["style"].get("text-color","#000000")
            thcolor= entry["style"].get("text-halo-color","#ffffff")
            thradius= entry["style"].get("text-halo-radius","0")
            tplace= entry["style"].get("text-position","center")
            toffset= entry["style"].get("text-offset","0")
            toverlap= entry["style"].get("text-allow-overlap",entry["style"].get("allow-overlap","false"))
            
            xml += xml_rule_start()
            xml += x_scale
            rulestring = " or ".join([ "("+ " and ".join([i.get_mapnik_filter() for i in rule]) + ")" for rule in entry["rule"]])
            xml += xml_filter(rulestring)
            xml += xml_textsymbolizer(ttext,tface,tsize,tcolor, thcolor, thradius, tplace, toffset,toverlap)
            sql.add(entry["sql"])
            itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
            xml += xml_rule_end()

      xml += xml_style_end()
      sql.discard("()")
      if sql:
        mfile.write(xml)
        if layer_type == "line":
          sqlz = " OR ".join(sql)
          itags = "\", \"".join(itags)
          itags = "\""+ itags+"\""
          sqlz = """with aaa as (SELECT %s, way FROM planet_osm_line where "%s" is not NULL and (%s)),
          bbb as (SELECT %s, way from aaa where way &amp;&amp; !bbox! )
          select %s, ST_LineMerge(ST_Union(way)) as way from bbb group by %s
          """%(itags,ttext,sqlz,itags,itags,itags)
          mfile.write(xml_layer("postgis-process", layer_type, itags, sqlz ))
        else:
          sql = " OR ".join(sql)
          mfile.write(xml_layer("postgis", layer_type, itags, sql ))
      else:
        xml_nolayer()

mfile.write(xml_end())