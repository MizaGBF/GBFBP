# Granblue Fantasy Battle Player  
* Local Server written in Python to play a custom Battle scene to play animations.  
* Tested on [Python 3.11](https://www.python.org/downloads/) or higher.  
  
![Preview](https://raw.githubusercontent.com/MizaGBF/GBFBP/main/data/preview.png)  
  
### Installation  
1. Download this repository and unzip (if needed) to a directory of your choice.  
2. (Windows) In the folder containing everything, SHIFT+right click, open a command prompt here or (Unix/Linux/Mac) open a terminal and navigate to the folder.
3. Type `python -m pip install -r requirements.txt` to install the required modules.  
  
### Usage  
This tool is a glorified animation viewer. It replicates a GBF battle scene and lets you load characters of your choice.  
On the `Run` tab, you can input up to 4 characters and 5 summons to load. It includes the following:
* Any valid playable character
* Any playable weapon (it will load a main character accordingly)
* Any playable main character class or skin
* Any valid playable summon
  
You must input the character or summon ID in the box. You can also try to input a name and it will automatically look it up on [gbf.wiki](https://gbf.wiki).  
One ID/name per line max.
It support styles (`_st2`), uncap (`_02`, `_03`, ...) and gender (`_gran`, `_djeeta`) strings. For example:
* `3040088000` will load Water Yngwie 0★ form.
* `3040088000_02` will load Water Yngwie 4★ form.
* `3040088000_03` will load Water Ynwgie 5★ form.
* `3040088000_st2` will load Water Ynwgie Style.  
* `3040506000_gran` will load the (default) Gran version of Himiko Toga.  
* `3040506000_djeeta` will load the Djeeta version of Himiko Toga.  
Those strings also work for weapons, summons and main characters as long as the according versions exist.  
  
Main characters have access to even more options:
* For example, the *Knight* class has the ID: `110001`.
* You can change the last digit to access the other colors: `110002` for gold, `110003` for blue, ...  
* For classes like *Viking*, you can get to the helmetless version by changing the last two digits to *80*: `100401` to `100480`.  
* You can also specify the proficiency to use:  `110001_sw` is Knight with a sword, `110001_sp` is Knight with a spear.  
* Strings are: sw, kn, sp, ax, wa, gu, me, bw, mc, kt (for sword, knife(dagger), spear, axe, wand(staff), gun, melee, bow, music(harp), katana).  
  
Try out [GBFAL](https://mizagbf.github.io/GBFAL/) to manually look for IDs.  
  
Once done, press the `Apply` button, wait. Once donc, press `OK` and open/reload the page.
  
### Command Line  
The application provides a minimal command interface if you want to run it in a terminal:  
`-port`: Followed by the port to set the server on.  
`-ssl`: To enable HTTPS. Abandoned and untested feature. Requires `domain.crt` and `domain.key` in the same folder.  
`-ani1`: Followed by a string. To set the first Custom Animation button.  
`-ani2`: Followed by a string. To set the second Custom Animation button.  
`-anitime`: Followed by a number. To set the Custom Animation durations.  
`-nogui`: To disable the GUI. It won't use your `settings.json`.  
`-battle`: Followed by multiple ID or names. It will load those elements as the battle scene to use. Only works if `-nogui` is set.  

### Skills  
The following skills are available in battle:  
* Toggle HP: Toggle a character HP between 1 and 100%
* Toggle Charge Bar: Toggle a character Charge Bar between 0 and 100%  
* Pose: Open the Animation sub menu (Only for characters, not weapons/classes entities) (See below):  
* Change Form: Toggle a character second form (This skill is only available for characters with a second form)  

The `Pose` skill gives you access to the following sub skills:
* Win: Play the first Win animation (if multiple available) or the default one  
* Win #2: Play the second Win animation (if available) or the default one  
* Damage: Play the damaged animation.  
* Down: Play the low HP animation.  
* Skill: Play all the skill animations in a row (if any).  
* Wait: Play the default Idle animation.  
* Custom 1: (for Advanced Users) Play the animations set in the `Custom 1` setting. Might crash the battle if used incorrectly.  
* Custom 2: (for Advanced Users) Play the animations set in the `Custom 2` setting. Might crash the battle if used incorrectly.  
  
### Settings  
* `Reload HTML` will generate a new `index.html` file based on the official one. If the battle doesn't load after a GBF update, try to press it.  
* `Clean Disk` will delete the `assets` folder. All assets will have to be re-downloaded.  
* `Clean Cache` will delete the files cached in memory.  
* `Background` lets you change the scene background. You can look the IDS up on [GBFAL](https://mizagbf.github.io/GBFAL/). Empty the setting to reset to the default.  
* `Enemy` lets you change the battle enemy. You can look the IDS up on [GBFAL](https://mizagbf.github.io/GBFAL/). Empty the setting to reset to the default.  
* `Checkerboard Background` will change the background to a checkboard one. Has priority over the Green Background.  
* `Green Background` will change the background to a checkboard one.  
  
Reload the page after changing the settings.  
  
### Animation  
This tab lets you edit the animations played by the `Custom 1` and `Custom 2` skills. It's only intended for advanced users.  
You can chain multiple animations by separating them with `;`.  
Reload the page if the page hangs after calling those skills, it means you set an incorrect value.  
  
### Other informations  
* Summons with multiple calls will cycle from one to the next.  
* Enemies attack will cycle between the auto attack animation, the single target special attacks and the AOE special attacks.
  
### Known Issues  
* Only one user can connect at a time to the server. More is untested and would cause issues.  
* The game only supports one mainhand weapon at a time. As a result, using multiple characters of different proficiencies is quite funny, see for yourself. It's sadly unfixable.  
* It doesn't support auxiliary weapons.  
* It doesn't support Enemies "full diamond" animations.  
* Mozilla Firefox should work but, as Granblue Fantasy is intended to be played with Chromium Browser, I can't guarantee it won't cause any issue.  
* Because of how the Class IDs work, newer classes and MC skins must be set manually in the code. An alternative would be to add in a request to the [GBFAL data.json](https://raw.githubusercontent.com/MizaGBF/GBFAL/main/json/data.json) to automatically update them but it's not my plans.  
* This tool can break if Cygames updates the game in a way which heavily modify it.  
  
### Frequently Asked Questions  
* Can you add <Insert wish list>?  
  
No, I'm not planning to support or update this project in any significant way.  
  
* Will I get in trouble for using it?  
  
The tool only requests the assets needed and patch them to make them work in a local environment. When the tool is running or when you're using the battle scene, you aren't making any request to the actual GBF at all.  
It doesn't have access to actual game data either, such as damage values, boss hp, etc...  
  
* Can I remove the HP bar?  
  
It's possible to make it near invisible but it's really annoying to do, so no.  
  
* Why is the summon shown as Fire when I press it?  
  
See above, the tool doesn't access any game data. As a result, it doesn't know the characters, summons, etc...'s elements.