#include <PololuMaestro.h>
#include <SoftwareSerial.h>
SoftwareSerial maestroSerial(10, 11);
MicroMaestro maestro(maestroSerial);

#define Min_Relevant_Distance 250
#define Close_Distance 400
#define Wait_Between_Actions 5000
#define Angle_Adjust 15
#define Servo_Limit_Low 992
#define Servo_Limit_High 2000

//Create info Arrays
unsigned int Angle_Array[50];
unsigned int Base_Array[50];
unsigned long TimeLastSeen_Array[50];

//Create Logic Arrays
boolean InView_Array[50];
boolean MinDist_Array[50];
boolean Greeted_Array[50];
boolean Called_Array[50];

//Variables
String data_string = "";
byte num_relevant_people = 0;
byte num_relevant_close_people = 0;
byte num_relevant_far_people = 0;
byte num_greeted_people = 0;
byte num_called_people = 0;
unsigned long last_action_time = 0;
byte action_case = 0;
boolean action_flag;
unsigned int temp_ID;
unsigned int temp_Angle;
unsigned int temp_Base;
unsigned long temp_TimeLastSeen;




String test = "";

/////////////////////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////SETUP////////////////////////////////////////////////////////
/////////////////////////////////////////////////////////////////////////////////////////////////////

void setup() {
  Serial.begin(9600);
  Serial.println("start");

  maestroSerial.begin(9600);
}


/////////////////////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////FUNCTIONS////////////////////////////////////////////////////
/////////////////////////////////////////////////////////////////////////////////////////////////////

void Target(byte i) {
  if (Angle_Array[i] * Angle_Adjust > (Servo_Limit_High * 4)) {
    maestro.setTarget(0, Servo_Limit_High * 4);
    Serial.print(" **** ANGLE ADJUST TOO HIGH **** ");
  }
  else if (Angle_Array[i] * Angle_Adjust > (Servo_Limit_Low * 4)) {
    maestro.setTarget(0, Servo_Limit_Low * 4);
    Serial.print(" **** ANGLE ADJUST TOO LOW **** ");
  }
  else {
    maestro.setTarget(0, Angle_Array[i] * Angle_Adjust);
  }
}

/////////////////////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////MAIN/////////////////////////////////////////////////////////
/////////////////////////////////////////////////////////////////////////////////////////////////////

void loop() {

  /////////////////////////////// GET INFO FROM PI ////////////////////////////////////////////////
  
  //Read a line of Serial Message if Available, use message to update a line in Info Arrays
  if (Serial.available() > 0) {
    //Read one line of serial message a a data entry
    String data_string = Serial.readStringUntil('\n');
    
    //Collect ID of this entry, modulus 50
    temp_ID = data_string.substring(4,14).toInt() % 50;

    //Collect Angle Position of this entry
    temp_Angle = data_string.substring(25,29).toInt();
    Angle_Array[temp_ID] = temp_Angle;

    //Collect Base Position of this entry
    temp_Base = data_string.substring(36,40).toInt();
    Base_Array[temp_ID] = temp_Base;

    //Collect Time Last Seen of this entry
    temp_TimeLastSeen = millis();
    TimeLastSeen_Array[temp_ID] = temp_TimeLastSeen;

    //Mark this entry as In View
    InView_Array[temp_ID] = 1;
  }









  /////////////////////////////// UPDATE LOGIC ARRAYS ////////////////////////////////////////////////
  //Reset count of number of relevant people
  num_relevant_people = 0;
  
  //Scan through all 50 IDs
  for (byte i = 0; i < 50; i++) {

    //If ID has not been seen in over 1 second, then mark them as not in view
    if (millis() - TimeLastSeen_Array[i] > 1000) {
      InView_Array[i] = 0;
      MinDist_Array[i] = 0;
    }
    
    //If ID has not been seen in over 60 seconds, then mark them as unGreeted and uncalled
    if (millis() - TimeLastSeen_Array[i] > 60000) {
      Greeted_Array[i] = 0;
      Called_Array[i] = 0;
    }
    
    //If ID is close enough to be relevent, then mark that they meet the minimum distance and update the count of relevant people
    if ((InView_Array[i] == 1) && (Base_Array[i] > Min_Relevant_Distance)) {
      MinDist_Array[i] = 1;
      num_relevant_people++;
    }
    //Else mark them as NOT meeting the minimum distance to be relevant
    else {
      MinDist_Array[i] = 0;
    }
  }




  /////////////////////////////// DECIDE ACTION ////////////////////////////////////////////////
  //Reset action_case
  action_case = -1;

  
  //Determine if it is time to perform an action
  if (millis() - last_action_time > Wait_Between_Actions) {
    last_action_time = millis();

    /////////////////////// NO RELEVANT PEOPLE //////////////////////////////////////
    //If there are ZERO relevant people
    if (num_relevant_people == 0) {
      //case 0 (Is anyone there?)
      action_case = 0;
    }


    /////////////////////// 1 RELEVANT PERSON //////////////////////////////////////
    //If there is ONE relevant person
    else if (num_relevant_people == 1) {
      //Scan array for ID of relevant person
      for (byte i =0; i < 50; i++) {
        //If ID is flagged as relevant
        if (MinDist_Array[i] == 1) {
          //If ID is close
          if (Base_Array[i] > Close_Distance) {
            //If ID is greeted
            if (Greeted_Array[i] == 1) {
              //case 3 (Continue Conversation)
              action_case = 3;
            }
            //Else ID is not greeted
            else {
              //case 1 (Greet)
              action_case = 1;
            }
          }
          //Else ID is far
          else {
            //case 2 (Call out to single person)
            action_case = 2;
          }
        }
      }
    }



    /////////////////////// MANY RELEVANT PEOPLE //////////////////////////////////////
    //Else there is MANY relevant people
    else {
      //Count number of relevent people Close Distance
      num_relevant_close_people = 0;
      for (byte i = 0; i < 50; i++) {
        if (Base_Array[i] > Close_Distance) {
          num_relevant_close_people++;
        }
      }

      //Count the amount of greeted people
      num_greeted_people = 0;
      for (byte i = 0; i < 50; i++) {
        if (Greeted_Array[i] == 1) {
          num_greeted_people++;
        }
      }

      //Count number of relevent people far away
      num_relevant_far_people = 0;
      for (byte i = 0; i < 50; i++) {
        if ((Base_Array[i] < Close_Distance) && (Base_Array[i] > Min_Relevant_Distance)) {
          num_relevant_far_people++;
        }
      }

      //Count the amount of called people
      num_called_people = 0;
      for (byte i = 0; i < 50; i++) {
        if (Called_Array[i] == 1) {
          num_called_people++;
        }
      }


      //If Relevant people NONE close
      if (num_relevant_close_people == 0) {
        //case 6 (Call out to many)
        action_case = 6;
      }


      //If ONE Relevant close person
      else if (num_relevant_close_people == 1) {

        //If not one greeted person
        if (num_greeted_people == 0) {
          //case 1 (Greet one person)
          action_case = 1;
        }

        //Else the one person has been greeted
        else {
          //If ONE relevant person far
          if (num_relevant_far_people == 1) {
            //IF the ONE has not been called
            if (num_called_people == 0) {
              //case 2 (call out to 1 person)
              action_case = 2;
            }
            //Else the one has been called out
            else {
              //case 3 (continue conversation)
              action_case = 3;
            }
          }
          //Else MANY relevant people are far
          else {
            //If over half of far relevant people have been called
            if (num_called_people > num_relevant_far_people / 2) {
              //case 3 (Continue conversation)
              action_case = 3;
            }
            //Else less than half have been called
            else {
              //case 4 (Call out to many to join us)
              action_case = 4;
            }
          }
        }
      }


      //Else Many Relevant people are close
      else {
        //If more than half have already been greeted
        if (num_greeted_people >= 0.5 * num_relevant_close_people) {
          //case 3 (Continue Conversation)
          action_case = 3;
        }
        else {
          //case 5 (Greet Many)
          action_case = 5;
        }
        
      }
    }
    
  }









  ///////////////////////////////////// DO ACTION ////////////////////////////////////
  switch (action_case) {
    case 0:
      // IDLE
      // Center the waist and do an idle animation
      Serial.print("Is anyone there? / IDLE");
      maestro.restartScript(0);
      //maestro.setTarget(0, (((Servo_Limit_High - Servo_Limit_Low) / 2) + Servo_Limit_Low) * 4); //Center Waist
      Serial.println();
      break;

      
    case 1:
      // Greet one person
      // Scan through IDs for one that is close, not greeted, and in view. BREAK AFTER FINDING
      for (byte i =0; i < 50; i++) {
        if ((Base_Array[i] > Close_Distance) && (Greeted_Array[i] == 0) && (InView_Array[i] == 1)) {
          Serial.print("Greet ONE person, ID: ");
          Serial.print(i);
          Greeted_Array[i] = 1; //Mark this person as Greeted AND Called
          Called_Array[i] = 1;
          maestro.restartScript(1);
          break;
        }
      }
      maestro.setTarget(0, 5000);////////////////////////////
      Serial.println();
      break;

      
    case 2:
      // Call out to 1 person
      // Scan through IDs for one that is not too far away, but still not too close, hasnt been called, and in view.
      // Don't Break after finding in case there is more than one ID that got caught in this action, label them all as "Called" and just target the last one
      action_flag = 0;
      for (byte i =0; i < 50; i++) {
        if ((Base_Array[i] > Min_Relevant_Distance) && (Base_Array[i] < Close_Distance) && (Called_Array[i] == 0) && (InView_Array[i] == 1)) {
          Serial.print("Call out to ONE person, ID: ");
          Serial.print(i);
          Called_Array[i] = 1; //Mark this person as Called
          action_flag = 1;
          maestro.restartScript(2);
          Target[i];
        }
      }
      //If 1 person called doesnt come, invite them to come closer
      //This should only occur if there is truly only one really shy person
      if (action_flag == 0) {
        for (byte i =0; i < 50; i++) {
          if ((Base_Array[i] > Min_Relevant_Distance) && (Base_Array[i] < Close_Distance) && (InView_Array[i] == 1)) {
            Serial.print("Its Ok, please come closer, ID: ");
            Serial.print(i);
            maestro.restartScript(2);
            Target[i];
          }
        }
      }
      Serial.println();
      break;

      
    case 3:
      // Continue Conversation
      // Scan IDs for one that is close and in view. BREAK AFTER FINDING
      // This results in talking to the first of 50 IDs
      for (byte i = 0; i < 50; i++) {
        if ((Base_Array[i] > Close_Distance) &&  (InView_Array[i] == 1)) {
          Serial.print("Continue Conversation with ID: ");
          Serial.print(i);
          maestro.restartScript(3);
          Target[i];
          break;
        }
      }
      Serial.println();
      break;

      
    case 4:
      // Call out to many to join us
      // Scan IDs for those that are not too close, but not too far, and in View
      Serial.print("Call out to many to join us");
      for (byte i = 0; i < 50; i++) {
        if ((Base_Array[i] < Close_Distance) && (Base_Array[i] > Min_Relevant_Distance) && (InView_Array[i] == 1)) {
          Called_Array[i] = 1; //Mark IDs as Called
          maestro.restartScript(4);
        }
      }
      Serial.println();
      break;


      
    case 5:
      // Greet Many
      // Scan IDs for those close and in view
      Serial.print("Greet this many: ");
      for (byte i = 0; i < 50; i++) {
        if ((Base_Array[i] > Close_Distance) && (InView_Array[i] == 1)) {
          Greeted_Array[i] = 1; //Mark IDs as greeted AND called
          Called_Array[i] = 1;
          Serial.print("x");
          maestro.restartScript(5);
        }
      }
      Serial.println();
      break;


      
    case 6:
      // Call out to many to join ME
      // Scan for IDs that are not too close, not too far, and in view
      Serial.print("Call out to many to join ME");
      for (byte i = 0; i < 50; i++) {
        if ((Base_Array[i] < Close_Distance) && (Base_Array[i] > Min_Relevant_Distance) && (InView_Array[i] == 1)) {
          Called_Array[i] = 1; //Mark IDs as called
          maestro.restartScript(6);
        }
      }
      Serial.println();
      break;
  }
}