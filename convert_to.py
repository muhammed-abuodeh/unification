import re
from pprint import pprint

from tools import read
import EMADA

# TODO include the BW map and cases
# TODO make read_map.py modular

# TODO handle DIAC, 
# diac has information that can help us determine whether lex for a pronoun is him or hum for example
# this is only for the case of MADA but we need to handle it 
# otherwise there would be loss of info in converting
# TODO handle the lex analysis of each "subword"



def main(map, input_tag):
    map_driver = read.read_map(map)

    #print(f"Conversion map: {map}\n")
    #print(f"Input tag: {input_tag}\n")
    
    matches = findAllMatches(input_tag, map_driver)
    if matches == []:
        return None
    
    output_tags = []
    for m in matches:
        src_vals = extractFeats(map_driver, m)
        EMADA_feats = convertFeats(src_vals, map_driver)
        EMADA_tag = orderTag(EMADA_feats, map_driver)
        EMADA_tag.addDefaults()

        if EMADA_tag not in output_tags:
            output_tags.append(EMADA_tag)
    #import pdb; pdb.set_trace()
    return output_tags

def cln_re_spcl_chrs(values):
    list = []
    for v in values:
        for i in "\\[]^$.?*+()/|":       # in case any regex chrs are in the values, expecially BW
            v = v.replace(i, f"\{i}")
        list.append(v)
    return list

def compileRE(map_driver):
    src_format = map_driver["format"]
    src_feats = map_driver["features"]

    for feat in src_feats:
        if feat in map_driver['map'] and '#VAL#' not in map_driver['map'][feat]:
            raw_values = cln_re_spcl_chrs(map_driver['map'][feat].keys())
            values = '(' + '|'.join(raw_values) + ')'
        else:
            values = "\\S+"
        src_format = src_format.replace(f"#{feat}#", f"(?P<{feat}>{values})", 1)

    #print(src_format)
    return src_format

def findAllMatches(input_tag, map_driver):
    src_format = compileRE(map_driver)
    m = findMatch(src_format, input_tag)
    if not m or m.group(0) != input_tag:
        return []
    else:
        matches = findMoreMatches(map_driver, m, src_format, input_tag)
    
    return matches

def findMatch(src_format, input_tag):
    src_re = re.compile(src_format)
    m = src_re.match(input_tag)
    return m

def compareMatches(map_driver, m1, m2):
    for feat in map_driver['features']:
        if m1.group(feat) and m1.group(feat) != m2.group(feat):
            return False
    
    return True

def findMoreMatches(map_driver, match, src_format, input_tag):
    matches = [match]
    
    for feat in match.groupdict():
        val = match.groupdict()[feat]
        if val:
            val = cln_re_spcl_chrs([val])[0]
            try:
                new_format = re.sub(f"(\\(\\?P<{feat}>(\\([^<]*\\||\\()){val}(\\||\\))", "\\g<1>\\g<3>", src_format)
            except:
                print("################################################")
                print(val)
                print(f"(\\(\\?P<{feat}>(\\([^<]*\\||\\()){val}(\\||\\))")
                print("################################################")
            new_format = new_format.replace("(|", "(")
            new_format = new_format.replace("||", "|")
            new_format = new_format.replace("|)", ")")
            if new_format != src_format:
                m = findMatch(new_format, input_tag)
                if m and m.group(0) == input_tag:
                    new_matches = findMoreMatches(map_driver, m, new_format, input_tag)
                    for m1 in new_matches:
                        for m2 in matches:
                            if not compareMatches(map_driver, m1, m2):
                                matches.append(m1)
            #new_format = src_format
    return matches

def extractFeats(map_driver, match):
    vals = {}
    for feat in map_driver['features']:
        if match.group(feat):
            vals[feat] = match.group(feat)

    return vals

def convertFeats(src_vals, map_driver):
    output = {}
    mapping = map_driver['map']
    for feat in src_vals.keys():
        if feat in mapping.keys():
            val = src_vals[feat]
            if val in mapping[feat].keys():
                for order in mapping[feat][val].keys():
                    if order not in output:
                        output[order] = EMADA.Subtag()
                    for outfeat in mapping[feat][val][order]:
                        output[order][outfeat] = mapping[feat][val][order][outfeat]

            elif "#VAL#" in mapping[feat].keys():
                for order in mapping[feat]["#VAL#"].keys():
                    if order not in output:
                        output[order] = EMADA.Subtag()
                    for outfeat in mapping[feat]["#VAL#"][order]:
                        output[order][outfeat] = mapping[feat]["#VAL#"][order][outfeat].replace("#VAL#", val)
    
    return output

def orderTag(trg_feats, map_driver):
    tag = EMADA.Tag()
    keys = [int(i) for i in trg_feats.keys()]
    keys.sort()
    keys = [str(i) for i in keys]
    base_order = int(map_driver['base_word_order'])
    
    for k in keys:
        tag.append(trg_feats[k])
        if int(k) == base_order:
            tag[-1]['orth'] = "base"
        elif int(k) < base_order:
            tag[-1]['orth'] = "proc"
        elif int(k) > base_order:
            tag[-1]['orth'] = "enc"

    return tag

def addDefaults(tag, def_tag):
    for subtag in tag:
        pos = subtag['pos']
        if pos not in def_tag:
            print(f"Error: pos {pos} not found in the defaults list")
        else:
            for feat in subtag:
                if subtag[feat] == '-1':
                    subtag[feat] = def_tag[pos][feat]

    return tag

if __name__ == "__main__":
    #map = "MADA_to_EMADA"
    #input_tag = "diac:wawAsiTatahum lex:wAsiTap pos:noun prc3:0 prc2:wa_conj prc1:0 prc0:0 per:na asp:na vox:na mod:na gen:f fgen:f num:s fnum:s stt:c cas:a enc0:3mp_poss rat:i"
    #input_tag = "diac:hw lex:huwa pos:pron prc3:0 prc2:0 prc1:0 prc0:0 per:3 asp:na vox:no mod:no gen:m fgen:m num:s fnum:s stt:no cas:no enc0:0 rat:na"
    map = "CAMeL_to_EMADA"
    input_tag = "PART+ADJ.MS+PRON"

    #map = "BW_to_EMADA"
    #input_tag = "Asm/NOUN+hA/POSS_PRON_3FS"
        
    output_tags = main(map, input_tag)
    
    print(f"The input tag maps to {len(output_tags)} tag(s) in EMADA:")
    for tag in output_tags:
        print("**************************")
        print(tag)