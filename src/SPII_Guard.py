# import 
from pytesseract import Output
import pytesseract
import argparse
import cv2
import matplotlib.pyplot as plt
import re
import spacy
from spacy import displacy
NER = spacy.load("en_core_web_sm")
import nltk
import os

import sys
import time as ti

pytesseract.pytesseract.tesseract_cmd = r'location\of\tesseract.exe'

ap = argparse.ArgumentParser()
ap.add_argument("-i", "--image", required=True,
	help="path to input image to be OCR'd")
ap.add_argument("-c", "--0", type=int, default=0,
	help="mininum confidence value to filter weak text detection")
args = vars(ap.parse_args(["--image", "receipt.jpg"]))

#Retrieve Image and File Name

image_location = r'location\of\image\file.jpg'
#image_location = "safeway-32085245240.jpg"
image = cv2.imread(image_location)
final_image = cv2.imread(image_location)

# get filename of original pdf
original_filename = os.path.basename(image_location).split('/')[-1]
# remove file extension
jpg_filename = os.path.splitext(original_filename)[0]


# Color correct and Instruct how to read/print out words on Receipt
rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
custom_config = r'--oem 3 --psm 6'
results = pytesseract.image_to_data(rgb, config=custom_config, output_type=Output.DICT)

#Ascii art info
def ascii_art(text):
    for index in range(len(text)):
        sys.stdout.write(text[index])
        sys.stdout.flush()
        ti.sleep(0.0008)
    print()


def ResizeWithAspectRatio(image, width=None, height=None, inter=cv2.INTER_AREA):
    dim = None
    (h, w) = image.shape[:2]

    if width is None and height is None:
        return image
    if width is None:
        r = height / float(h)
        dim = (int(w * r), height)
    else:
        r = width / float(w)
        dim = (width, int(h * r))

    return cv2.resize(image, dim, interpolation=inter)


window_name = 'Image'

# loop over each of the individual text localizations
data = []
#print(len(results["text"]))
for i in range(0, len(results["text"])):
	# extract the bounding box coordinates of the text region from
	# the current result
	x = results["left"]
	y = results["top"]
	w = results["width"]
	h = results["height"]
 
	# extract the OCR text itself along with the confidence of the
	# text localization
	text = results["text"]
	coordinate = cv2.rectangle(image, (x[i], y[i]), (x[i] + w[i], y[i] + h[i]), (255, 0, 0), 2)
	#print(((x[i], y[i]), (x[i] + w[i], y[i] + h[i]), (0, 0, 255), 2), text[i])

	group = [((x[i], y[i]), (x[i] + w[i], y[i] + h[i]), (0, 0, 255), 2), text[i]]
	
	data.append(group)
	conf = int(results["conf"][i])

#print(coordinate)
# plt.imshow(coordinate)
cv2.imwrite(jpg_filename +'.jpg', coordinate)
resize_1 = ResizeWithAspectRatio(coordinate, width=300)
cv2.imshow(window_name, resize_1)
cv2.waitKey(5000)
cv2.destroyAllWindows()

new_data = []
for x in data:
    space = re.findall("\S", x[1])
    #print(x[1])
    #print(x)
    
    if space:
        new_data.append(x)
        #print(x)
        
print("Number of words/numbers/phrases detected:", len(new_data))
for x in data:
    print(x[1])
    
# Detect Sensitive information with Regular Expressions and Named Entity Recognition
key_words = []
not_names = ["SAM'S", "ACTIVATION", "sam", "Sam's", "Ross", "Cashier", "Reg", "Shk", "Salesperson", "Walmart", "Costco", "Amazon", "Aldi", "Home Depot", "Target", "Walgreens", "Best Buy", "Dollar general", "IKEA", "Kroger", "7-Eleven", "Macy's", "Verizon", "CVS", "Lowe's", "Albertsons", "Apple", "Royal Ahold Delhaize USA", "Publix", "Best Buy", "TJX", "Dollar General", "H.E. Butt", "Dollar Tree", "Ace Hardware", "At&t", "AT&T", "Meijer", "BJ's", "Ross", "Wakefern", "Rite Aid", "Kohl's", "Nordstrom", "Tractor Supply", "Gap", "GAP","GAp", "gap", "Dillard's", "McDonald", "Starbucks", "Subway", "Taco Bell", "Chick-fil-A", "Wendy's", "Burger King", "Dunkin", "Domino's", "Panera Bread", "Pizza Hut", "Chipotle", "Sonic", "KFC", "kfc", "Arby's", "Little Caesars", "Dairy Queen", "Jack in the Box", "Panda Express", "Panda", "panda", "Popeyes", "popeyes", "Papa John's", "Whataburger", "Jimmy John's", "Hardee's", "Zaxby's", "Five Guys", "five guys", "Culver's", "Carl's Jr", "Bojangles", "Wingstop", "Cane's", "COUNTER-Eat", "Raising Cane's" ]

# Save new file with boxes around sensitive information
cv2.imshow(window_name, resize_1)
cv2.waitKey(3000)
cv2.destroyAllWindows()


for y, x in enumerate(data):
  # replace regex with LSTM

  date = re.findall("^[0-9].+/.[0-9]$", x[1])
  date2 = re.findall("[0-9].+/.[0-9]", x[1])
  #date2 = re.findall("^[0-9][0-9]+-[0-9]$", x[1]) Confused with phone numbers
  time = re.findall("[0-9].+:.[0-9]", x[1])
  time2 = re.findall("[0-9]+:[0-9][0-9]", x[1])
  #digits_1 = re.search("XXXXXXXXXX*..[0-9][0-9][0-9]", x[1])
  
  digits_1 = re.search("[X][X]..[0-9][0-9][0-9]", x[1])
  digits_2 = re.findall("[x][x]", x[1])
  digits_3 = re.findall("[K][K]", x[1])
  digits_y = re.findall("...[0-9][0-9]", x[1])
  digits_x = re.search("^[0-9]..[0-9]$", x[1])
  
  
  text_NER = NER(x[1])
  
  if digits_1:
      key_words.append(x)
      #print("This is appended", x)
      print("This is the last 4 digits: ", x)
  else:
      pass
    
  if digits_2:
      #print("it's a digits_2", x)
      if digits_y:
        key_words.append(x)
        print("This is the last 4 digits: ", x )
      else:
          if(y<len(data)-1):
            y = y+1
            #print("this is the next:", data[y][1])
            z = data[y]
            #print("this is the next x", x)
            if re.search("^[0-9]..[0-9]$", z[1]):
              key_words.append(z)
              print("This is last 4 digits: ", data[y])
              pass
            #key_words.append(next)
        #print("This is appended", x)
            else:
              pass
          else:
            pass
  
  if digits_2:
    key_words.append(x)
    print("This is the last 4 digits: ", x)
  else:
    pass     
  
    
  if digits_3:
      key_words.append(x)
      #print("This is appended", x)
      print("This is the last 4 digits: ", x)
  else:
      pass

  if date:
    key_words.append(x)
    print("This is a date:", x)
    #print("test")
  else:
    pass
  
  if date2:
    key_words.append(x)
    print("This is date2: ", x)
  else:
    pass
  
  if time:
    key_words.append(x)
    print("This is time: ", x)

  else:
    pass
  
  if time2:
    key_words.append(x)
    print("This is time2: ", x)

  else:
    pass

  for word in text_NER.ents:
    if word.label_ == "PERSON":
        if word.text in not_names:
          break
        else:
          key_words.append(x)
          print("This is a person: ", x)
          
        
    else:
      pass

#print(key_words)

                           
ascii_art('                          @@@@@@')                                             
ascii_art('                        @@@@@@@@@%       @@  @@ @@ #@@@ @@    @@@  *@@@   #@  @#  @@@')                                   
ascii_art('                       @@        @@      *@  @  @  #@   @@   @@ #  @. @@  @@=:@@  @=') 	                         
ascii_art('                      @@ @        @@      @  @  @  #@@@ @@   @    @@   @  @ @ .@  @@@')                     
ascii_art('                      @@ @        @@      @@@@@@@  #@   @@   @    *@  =@  @ @  @  @=')   	              
ascii_art('                       @# @@@     @@      @@   @%  #@@@ @@@@ %@@@  @@@@-  @ @  @  @@@')                                       
ascii_art('                         #@@@@@%%')                                           
ascii_art('                              %@%         @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')                                            
ascii_art('                               @@%        @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')                                           
ascii_art('                                @%-')                                                                          
ascii_art('                                 @%-')  
 
# Keep location of the sensitive words
window = 'Detected'
location = []
for x in key_words:
    where = x[0]
    #print(x[0])
    location.append(where)
    
#print(location)

# Draw boxes around sensitive words
for x in location:
    #print(x[3])
    draw = cv2.rectangle(final_image, x[0], x[1], x[2], x[3])
    #print("this is draw", type(draw)) 



cv2.imwrite(jpg_filename + '_detect' +'.jpg', draw)
#imS = cv2.resize(draw, (960, 540)) 
resize = ResizeWithAspectRatio(draw, width=300)
cv2.imshow(window, resize)
cv2.waitKey(10000)
cv2.destroyAllWindows()



    
    