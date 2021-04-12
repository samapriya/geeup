# Cookies Setup

This method was added since v0.4.6 and uses a third party chrome extension to simply code all cookies. The chrome extension is simply the first one I found and is no way related to the project and as such I do not extend any support or warranty for it.

The chrome extension I am using is called [Copy Cookies and you can find it here](https://chrome.google.com/webstore/detail/copy-cookies/jcbpglbplpblnagieibnemmkiamekcdg/related)

It does exactly one thing, copies cookies over and in this case we are copying over the cookies after logging into [code.earthengine.google](https://code.earthengine.google.com)

![cookie_copy](https://user-images.githubusercontent.com/6677629/114257576-8de20780-9986-11eb-86c5-4c85e35367c3.gif)

**Import things to Note**

* Open a brand new incognito or a browser window while you are copying cookies, if you have multiple GEE accounts open on the same browser the cookies being copied may create some read issues at GEE end.
* Clear cookies and make sure you are copying cookies from [code.earthengine.google](https://code.earthengine.google.com) in a fresh browser instance if upload fails with a ```Unable to read``` error.
* Make sure you save the cookie for the same account which you initiliazed using earthengine authenticate

To run cookie_setup and to parse and save cookie user

```
geeup cookies_setup
```

* For **Bash** the cannonical mode will allow you to only paste upto 4095 characters and as such geeup cookie_setup might seem to fail for this use the following steps

* Disable cannonical mode by typing ```stty -icanon``` in terminal
* Then run ```geeup cookie_setup```
* Once done reenable cannonical mode by typing ```stty icanon``` in terminal

**Since cookies generated here are post login, theoretically it should work on accounts even with two factor auth or university based Single Sign on GEE accounts but might need further testing**
