// Helping doorknob
// ECE-4320 Architectural Robotics
// John Walter & Evonne Weeden

// Note: the Arduino's EEPROM is used to save the threshold and average maximum force
// to allow data integrity between powering cycles of the Arduino

#include <EEPROM.h>
#define THRESH 30   // digital minimum base threshold if one note set
#define LATCH 2     // digital pin for the solenoid latch
#define DOOR 3      // digital pin for the door status (open or closed)
#define SETUP 4     // digital pin for the switch to toggle setup mode
#define FSENSOR A8  // analog pin for the force sensor input

#define THRESH_ADDR 1 // EEPROM address for threshold 
#define AVG_ADDR 2    // EEPROM address for average maximum force

int threshold = 0;
int itteration = 0;
int maximum = 0;
int max_forces[5];
int max_total = 0;
int lastmax = 0;
int latch_status = 0;

void setup() {
  Serial.begin(9600);
  // set door pin to input
  pinMode(DOOR,INPUT);
  // set latch pin to output
  pinMode(LATCH,OUTPUT);
  // set setup pin to input
  pinMode(SETUP,INPUT);
  // read saved threshold from memory
  int old_thresh = EEPROM.read(THRESH_ADDR);
  // if no old threshold exists, use the base threshold
  if(old_thresh == 255){
    threshold = THRESH;
  // otherwise use the old threshold
  }else{
    threshold = old_thresh;
  }
}

// This function toggles the solenoid latch
// to allow the door to either be open or latched shut.
void toggleLatch(){
  // if latch is not active, activate
  if(latch_status == 0){
    latch_status = 1;
    digitalWrite(LATCH,HIGH);
  // if latch is active, deactivate
  }else{
    latch_status=0;
    digitalWrite(LATCH,LOW);
  }
}

void loop() {
  // if SETUP switch is HIGH, allow the user to setup a base threshold by squeezing the knob
  // To use this functionality, you must:
  //  (1) switch the setup switch on
  //  {2} press the Arduino's reset button
  //  (3) squeeze the knob hard
  //  (4) turn the switch off
  //  (5) press the reset button again
  // This process measures the maximum squeezed force experienced, takes 60% of it, and makes that
  // value the new threshold value
  if(digitalRead(SETUP) == HIGH){
    int maximum = 0;
    // wait for user to start squeezing knob
    int force = analogRead(A8);
    while(force < 10){force = analogRead(A8);delay(50);}
    delay(50);
    // once user is squeezing
    while(force > 10){
      // determine maximum force encountered
      if(force > maximum){
        maximum = force;
      }
      delay(50);
      force = analogRead(A8);
    }
    // set threshold as 60% of the encountered maximum force
    threshold = maximum*.6;
    // write new threshold to EEPROM
    EEPROM.write(THRESH_ADDR,threshold);
  // if not in setup mode
  }else{
    int maximum = 0;
    // wait for the force on the knob to become greater than the threshold
    int force = analogRead(A8);
    while(force < threshold){force = analogRead(A8);delay(100);}
    delay(100);
    // toggle door latch (open)
    toggleLatch();
    // while force on knob is greater than the threshold (the user is squeezing the knob), determine maximum force encountered
    while(force > threshold){
      // determine max force on knob
      if(force > maximum){
        maximum = force;
      }
      force = analogRead(A8);
      delay(50);
    }
    // wait for door to be opened 
    while(digitalRead(DOOR) == HIGH){
      //Serial.println("LOW");
      delay(50);
    }
    delay(100);
    // wait for door to be closed
    while(digitalRead(DOOR) == LOW){
      //Serial.println("HIGH");
      delay(50);
    }
    // once closed, toggle door latch (close)
    toggleLatch();
    // as long as maximum is not 0 (a valid maximum force was established)
    if(maximum != 0){
      // save maximum force into an array
      max_forces[itteration] = maximum;
      // keep a sum of the max forces for the average calculation
      max_total = max_total+maximum;
      // increase the itteration (1-5)
      itteration++;
      // if itteration equals 5, determine the average of the last 5 maximum forces
      // # Below basically looks at how strong the user is squeezing the knob during the
      // # last 5 uses, takes the average of those 5 values, and then compares the new average with
      // # the last average to adapt the threshold accordingly.
      if(itteration == 5){
        // calculate average
        int max_avg = max_total/5;
        // read old average from the previous 5 uses from memory
        int old_avg = EEPROM.read(AVG_ADDR);
        // save new average in memory
        EEPROM.write(AVG_ADDR,max_avg);
        // if new average < old average, decrease threshold by 5 (person is getting weaker)
        if((old_avg != 0) & (max_avg < old_avg)){
          //Serial.println("Change threshold");
          threshold-=5;
        }
        // if new average > old average, increase threshold by 5 (person is getting stroner)
        if(max_avg > old_avg){
          threshold+=5;
        }
        // save new threshold to memory
        EEPROM.write(THRESH_ADDR,threshold);
        // reset itteration counter for another 5 uses
        itteration = 0;
        // clear the max total
        max_total = 0;
      }
      // save the maximum 
      lastmax = maximum;
    // if an invalid maximum was established, use the previous maximum value
    }else{
      maximum = lastmax;
    }
    // write the threshold and maximum over serial 
    Serial.print(threshold);
    Serial.print(",");
    Serial.println(maximum);
  }
}
