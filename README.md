AutoDBD
=======
###1. Install some package:

<pre><code>sudo apt-get install python-pip  
sudo pip install BeautifulSoup4  
sudo pip install gspread  
</code></pre>
####Windows
If you want running on windows, need some setting
<pre><code>1. Install python  
2. Install git windows version  
3. Setting Home environ  
4. Download and run https://raw.github.com/pypa/pip/master/contrib/get-pip.py  
5. Install BeautifulSoup4 and gspread  
6. Running using "pythyon AutoDBD.py --nodaemon"
</code></pre>

###2. Put files in your PC
<pre><code>$ cd ~  
$ git clone https://github.com/codediablos/AutoDBD  
$ cp ~/AutoDBD/.AutoDBD.conf ~/.AutoDBD.conf  
</code></pre>

###3. Motify your config  
<pre><code>$ vi ~/.AutoDBD.conf  
</code></pre>
#### AutoTimeCard ####
Set `timecard = y` to use auto-time card  
Project state will get from   
[https://docs.google.com/spreadsheet/ccc?key=0AkLncPMATEhwdGRjejdRcEhFazNTc0plZ3dpb0twTmc](https://docs.google.com/spreadsheet/ccc?key=0AkLncPMATEhwdGRjejdRcEhFazNTc0plZ3dpb0twTmc)  
Your need to set `random_project` by this side  


###4. Start service  
Your can add below line to your .bashrc  
<pre><code>python AutoDBD/AutoDBD.py start  
</code></pre>

Using below command to test (fill today task immediately)

<pre><code>python AutoDBD/AutoDBD.py -g -t  
</code></pre>

And there have some logs in ~/.AutoDBD.log