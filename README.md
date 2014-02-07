AutoDBD
=======
###1. Install some package:

<pre><code>sudo apt-get install python-pip  
sudo pip install BeautifulSoup4  
sudo pip install gspread  
</code></pre>

###2. Put files in your linux  
<pre><code>$ cd ~  
$ git clone https://github.com/codediablos/AutoDBD  
$ cp ~/AutoDBD/.AutoDBD.conf ~/.AutoDBD.conf  
</code></pre>

###3. Motify your config  
<pre><code>$ vi ~/.AutoDBD.conf  
</code></pre>
#### AutoTimeCard ####
Project state will get from   
[https://docs.google.com/spreadsheet/ccc?key=0AkLncPMATEhwdGRjejdRcEhFazNTc0plZ3dpb0twTmc](https://docs.google.com/spreadsheet/ccc?key=0AkLncPMATEhwdGRjejdRcEhFazNTc0plZ3dpb0twTmc)  
Your need to set `random_project` by this side  


###4. Start service  
Your can add below line to your .bashrc  
<pre><code>python AutoDBD/AutoDBD.py start  
</code></pre>

And there have some logs in ~/.AutoDBD.log